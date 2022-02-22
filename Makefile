all: function.zip

function.zip: update-ddns-record
	rm -f $@; zip $@ $^

update-ddns-record: main.go
	go build

update: function.zip
	aws-vault exec lars -- aws lambda update-function-code \
		--function-name update-ddns-record \
		--zip-file fileb://function.zip
