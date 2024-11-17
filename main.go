package main

import (
	"Nexus/data"
	"Nexus/strategies"
	"log"
	"os"
	"github.com/joho/godotenv"
)

func main() {
	log.Println("**********************************")
	log.Println("**********************************")
	log.Println("********* STARTING NEXUS *********")
	log.Println("**********************************")
	log.Println("**********************************")
	godotenv.Load(".env")
	if os.Getenv("DATA") != "" {
		log.Println("--------------- STARTING UP DATA SERVICE ---------------")
		data.DataService()
	} else if os.Getenv("REVERSION") != "" {
		log.Println("--------------- STARTING UP REVERSION SERVICE ---------------")
		strategies.ReversionService()
	} else {
		log.Println("No service specified... ending Nexus")
	}
}