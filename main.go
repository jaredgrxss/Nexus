package main

import (
	"Nexus/data"
	"Nexus/strategies"
	"log"
	"os"
	"github.com/joho/godotenv"
)

func main() {
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
		data.DataService()
	case "Reversion":
		log.Println("--------------- STARTING UP REVERSION SERVICE ---------------")
		strategies.ReversionService()
	}
}