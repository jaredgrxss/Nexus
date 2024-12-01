package helpers

import (
	"encoding/json"
	"os"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/sns"
	"github.com/aws/aws-sdk-go/service/sqs"
)

/* 
	global sessions to be reused for a specific service,
	so that we don't have to keep creating new sessions
*/
var sess *session.Session
var snsClient *sns.SNS
var sqsClient *sqs.SQS

// use a shared session to avoid too many connections open across the system
func createOrReturnAWSSession() (*session.Session, error) {
	if sess == nil {
		newSession, err := session.NewSession(&aws.Config{
			Region: aws.String(os.Getenv("REGION")),
		})
		if err != nil {
			return nil, err
		}
		sess = newSession
	}
	return nil, nil
}

// create a new sns connection or reuse exisitng connection based on data type
func createOrReturnSNSClient() (*sns.SNS, error) {
	if snsClient == nil {
		_, err := createOrReturnAWSSession()
		if err != nil {
			return nil, err
		}
		snsClient = sns.New(sess)
	} 
	return snsClient, nil
}	

// given a specific SNS topic, publish data 
func PublishSNSMessage(data string, topicArn string) (string, error) {
	// make sure client connections are active
	_, err := createOrReturnSNSClient()
	if err != nil {
		return "", err
	}
	result, err := snsClient.Publish(&sns.PublishInput{
		Message: aws.String(data),
		TopicArn: aws.String(topicArn),
	})
	if err != nil {
		return "", err 
	}
	return *result.MessageId, nil
}

// establish a new sqs client for polling
func createOrReturnSQSClient() (*sqs.SQS, error) {
	if sqsClient == nil {
		_, err := createOrReturnAWSSession()
		if err != nil {
			return nil, err
		}
		sqsClient = sqs.New(sess)
	}
	return sqsClient, nil
}

// used to poll a queue message for a given queue
func PollSQSMessage(queueUrl string) ([]*sqs.Message, error) {
	// make sure client connections are active
	_, err := createOrReturnSQSClient()
	if err != nil {
		return nil, err
	}
	// poll the sqs for the latest data
	output, err := sqsClient.ReceiveMessage(&sqs.ReceiveMessageInput{
		QueueUrl: aws.String(queueUrl),
		MaxNumberOfMessages: aws.Int64(1),
		WaitTimeSeconds: aws.Int64(20),
		VisibilityTimeout: aws.Int64(30),
	})
	if err != nil {
		return nil, err
	}
	return output.Messages, nil
}

// used to delete a specific SQS message 
func DeleteSQSMessage(queueUrl string, message *sqs.Message) error {
	// make sure client connections are active
	_, err := createOrReturnSQSClient()
	if err != nil {
		return err
	}
	// delete an sqs message
	_, err = sqsClient.DeleteMessage(&sqs.DeleteMessageInput{
		QueueUrl: aws.String(queueUrl),
		ReceiptHandle: message.ReceiptHandle,
	})
	if err != nil {
		return err
	}
	return nil
}

// used to subscribe a specific SQS arn to a specific SNS arm
func SubscribeSQSToSNS(queueArn string, queueUrl string, snsArn string) error {
	// make sure client connections are active
	_, err := createOrReturnSQSClient()
	if err != nil {
		return err
	}
	_, err = createOrReturnSNSClient()
	if err != nil {
		return err
	}
	// create policy if doesn't exist already
	policy := map[string]interface{}{
		"Version": "2012-10-17",
		"Statement": []map[string]interface{}{
			{
				"Effect": "Allow",
				"Principal": "*",
				"Action": "sqs:SendMessage",
				"Resource": queueArn,
				"Condition": map[string]interface{}{
					"ArnEquals": map[string]interface{}{
						"aws:SourceArn": snsArn,
					},
				},
			},
		},
	}
	policyJSON, err := json.Marshal(policy)
	if err != nil {
		return err
	}

	// set policy on given SQS
	_, err = sqsClient.SetQueueAttributes(&sqs.SetQueueAttributesInput{
		QueueUrl: aws.String(queueUrl),
		Attributes: map[string]*string{
			"Policy": aws.String(string(policyJSON)),
		},
	})
	if err != nil {
		return err
	}

	// subscribe SQS -> SNS 
	_, err = snsClient.Subscribe(&sns.SubscribeInput{
		Protocol: aws.String("sqs"),
		TopicArn: aws.String(snsArn),
		Endpoint: aws.String(queueArn),
	})
	if err != nil {
		return err
	}
	return nil 
}