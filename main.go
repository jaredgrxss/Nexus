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
	switch (os.Getenv("Service")) {
	case "Data":
		log.Println("--------------- STARTING UP DATA SERVICE ---------------")
		data.DataService()
	case "Reversion":
		log.Println("--------------- STARTING UP REVERSION SERVICE ---------------")
		strategies.ReversionService()
	}
}