package strategies

import (
	"Nexus/helpers"
	"log"
	"os"
)

func ReversionService() {
	for {
		// make sure reversion SQS is subscribed to the data SNS
		err := helpers.SubscribeSQSToSNS(os.Getenv("REVERSION_SQS_ARN"), os.Getenv("REVERSION_SQS_URL"), os.Getenv("DATA_SNS"))
		if err != nil {
			log.Println("Error in subscribing to SNS data topic", err)
			return
		}
		// get all messages from SQS
		messages, err := helpers.PollSQSMessage(os.Getenv("REVERSION_SQS_URL"))
		if err != nil {
			log.Println("Error in receiving SQS message", err)
		}
		// loop and extract data
		for _, message := range messages {
			log.Printf("Received SNS message: ID=%s, Body=%s\n", *message.MessageId, *message.Body)
			err := helpers.DeleteSQSMessage(os.Getenv("REVERSION_SQS_URL"), message)
			if err != nil {
				log.Println("Error in deleting SQS message", err)
			}
			log.Printf("Message successfully deleted!")
		}
	}
}