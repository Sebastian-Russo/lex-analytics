Flow: (everything labled with aci-ccass-lex-analytics)

S3 /inputs >
Sends data through s3_path instead
Download csv (test cases)

Initializer lambda >
 Kick off test here
Test gives s3 path

SQS >
Processor lambda >
	Code from Sagemaker example (compare)
	Check logs after kick off test

Kinesis Firehose >
S3 /results & /errors
Athena

