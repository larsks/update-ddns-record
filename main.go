package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/route53"
)

func HandleRequest(ctx context.Context, request events.APIGatewayProxyRequest) (string, error) {
	update_token := os.Getenv("DDNS_UPDATE_TOKEN")
	hosted_zone_id := os.Getenv("DDNS_HOSTED_ZONE_ID")

	if len(update_token) == 0 || len(hosted_zone_id) == 0 {
		return NewResponse("error", "Missing required configuration").String(), nil
	}

	clientAddress := request.Headers["x-forwarded-for"]
	if len(clientAddress) == 0 {
		return NewResponse("error", "Unknown client address").String(), nil
	}

	hostName := request.QueryStringParameters["hostname"]
	req_token := request.QueryStringParameters["token"]
	sess := session.Must(session.NewSession())
	svc := route53.New(sess)

	log.Printf("checking request from %s for %s", clientAddress, hostName)
	if req_token != update_token {
		return NewResponse("error", "Invalid udpate token").String(), nil
	}

	log.Printf("updating %s in zone %s", hostName, hosted_zone_id)

	changes := route53.ChangeResourceRecordSetsInput{
		HostedZoneId: aws.String(hosted_zone_id),
		ChangeBatch: &route53.ChangeBatch{
			Changes: []*route53.Change{
				{
					Action: aws.String("UPSERT"),
					ResourceRecordSet: &route53.ResourceRecordSet{
						Name: aws.String(hostName),
						Type: aws.String("A"),
						TTL:  aws.Int64(300),
						ResourceRecords: []*route53.ResourceRecord{
							{
								Value: aws.String(clientAddress),
							},
						},
					},
				},
			},
		},
	}

	resp, err := svc.ChangeResourceRecordSets(&changes)
	if err != nil {
		return NewResponse(
			"error", "Failed to update record",
			WithApiResult(err.Error()),
		).String(), nil
	}

	return NewResponse("success",
		fmt.Sprintf("Updated address for %s", hostName),
		WithHostInfo(hostName, clientAddress),
		WithApiResult(resp.String()),
	).String(), nil
}

func main() {
	lambda.Start(HandleRequest)
}
