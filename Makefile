GOFILES = $(wildcard *.go)

all: update-ddns-record

.INTERMEDIATE: function.zip
function.zip: update-ddns-record
	zip $@ $^

update-ddns-record: $(GOFILES)
	go build

update: .lastupdate

.lastupdate: function.zip
	aws lambda update-function-code \
		--function-name update-ddns-record \
		--zip-file fileb://function.zip
	touch $@

clean:
	rm -f update-ddns-record function.zip .lastupdate
