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
		to run locally, set local=true
	*/
	if os.Getenv("local") != "true" {
		passphrase, err := helpers.RetrieveSecret(os.Getenv("passphrase"))
		if err != nil {
			log.Println("Error in retreiving passphrase", err)
			return
		}
		err = helpers.DecryptEnvFile(passphrase, os.Getenv("env-file"))
		if err != nil {
			log.Println("Error decrypting env file:", err)
		}
		// load envs
		err = godotenv.Load(".env")
		if err != nil {
			log.Println("Error loading envioronment variables:", err)
			return
		}
	}
	// load envs
	err := godotenv.Load(".env")
	if err != nil {
		log.Println("Error loading envioronment variables:", err)
		return
	}
	// spin up respective service
	switch (os.Getenv("Service")) {
	case "Data":
		log.Println("--------------- STARTING UP DATA SERVICE ---------------")
		services.DataService()
	case "Reversion":
		log.Println("--------------- STARTING UP REVERSION SERVICE ---------------")
		services.ReversionService()
	}
}