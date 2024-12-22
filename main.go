package main

import (
	"Nexus/services"
	"Nexus/helpers"
	"log"
	"os"
	"github.com/joho/godotenv"
)

func main() {
	/* 
		decrypt specified env file with specified passphrase
	   	env specification is controlled at the task definition level
		to run locally, set the env variable
		1. passphrase=the passphrase for the env file
		2. env-file=the env file to decrypt
	*/
	if os.Getenv("LOCAL") == "true" {
		// just skip directly to decrypting the env file
		err := helpers.DecryptEnvFile(os.Getenv("PASSPHRASE"), os.Getenv("ENV_FILE")) 
		if err != nil {
			log.Println("Error decrypting env file:", err)
			return
		}
	} else { // running in ECS, use secrets manager and task definition envs
		// fetch the passphrase from secrets manager
		passphrase, err := helpers.RetrieveSecret(os.Getenv("PASSPHRASE"))
		if err != nil {
			log.Println("Error in retreiving passphrase:", err)
			return
		}
		err = helpers.DecryptEnvFile(passphrase, os.Getenv("ENV_FILE"))
		if err != nil {
			log.Println("Error decrypting env file:", err)
		}
	}
	// load envs now that the env file is decrypted
	err := godotenv.Load(".env")
	if err != nil {
		log.Println("Error loading envioronment variables:", err)
		return
	}
	log.Println("Environment variables loaded successfully")
	// spin up respective service
	switch (os.Getenv("SERVICE")) {
	case "Data":
		log.Println("--------------- STARTING UP DATA SERVICE ---------------")
		services.DataService()
	case "Reversion":
		log.Println("--------------- STARTING UP REVERSION SERVICE ---------------")
		services.ReversionService()
	}
}