package main  

import (
	"log"
	"github.com/joho/godotenv"
	"Nexus/data"
)

func main() {
	log.Println("**********************************")
	log.Println("**********************************")
	log.Println("********* STARTING NEXUS *********")
	log.Println("**********************************")
	log.Println("**********************************")
	godotenv.Load(".env")
	data.DataService()
}