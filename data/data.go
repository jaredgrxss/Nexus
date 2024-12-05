package data

import (
	"context"
	"encoding/json"
	"log"
	"os"
	"os/signal"
	"time"
	"Nexus/helpers"
	"github.com/alpacahq/alpaca-trade-api-go/v3/marketdata"
	"github.com/alpacahq/alpaca-trade-api-go/v3/marketdata/stream"
)

// struct to hold live trade information
type TradeData struct {
	Exchange string
	Condition []string
	ID int64
	Price float64
	Size uint32
	Symbol string
	Tape string
	Timestamp time.Time
}

// struct to hold live quote information
type QuoteData struct {
	AskExchange string
	AskPrice float64 
	AskSize uint32
	BidExchange string
	BidPrice float64 
	BidSize uint32 
	Conditions []string
	Symbol string 
	Tape string
	Timestamp time.Time
}

// struct to hold live bar information
type BarData struct {
	Close float64
	High float64
	Low float64
	Open float64
	Symbol string 
	Timestamp time.Time
	TradeCount uint64
	VWAP float64
	Volume uint64
}

func DataService() {
	// check to see if market is open
	for {
		isMarketOpen, err := helpers.IsMarketOpen()
		if err != nil {
			log.Printf("Failed to wait for market open: %v", err)
			time.Sleep(10 * time.Second)
			continue
		}

		// market is not open, wait before trying to establish a connection
		if !isMarketOpen {
			log.Println("Market is not open yet...")
			time.Sleep(1 * time.Minute)
			continue
		}

		ctx, cancel := context.WithCancel(context.Background())
		defer cancel()

		// setting up cancelling upon keyboard interrupt
		s := make(chan os.Signal, 1)
		signal.Notify(s, os.Interrupt)
		go func() {
			<-s
			cancel()
		}()
		
		log.Println("Trying to connect to broker data stream")
		// set up client and add listeners for universe
		streamClient := stream.NewStocksClient(
			marketdata.IEX,
			stream.WithTrades(tradeHandler, "AAPL"),
			stream.WithQuotes(quoteHandler, "AAPL"),
			stream.WithBars(barHandler, "AAPL"),
			stream.WithCredentials(os.Getenv("BROKER_PAPER_API_KEY"), os.Getenv("BROKER_PAPER_SECRET_KEY")),
		)

		// add logic to subscribe to trades, quotes, and bars for a list of stocks here
		
		// connect to brokerage
		if err := streamClient.Connect(ctx); err != nil {
			log.Fatal("Could not establish connection with error: ", err)
		}
		log.Println("Established brokerage connection!")

		// check to see if brokerage terminated our connection
		go func() {
			err := <-streamClient.Terminated()
			if err != nil {
				log.Println("Connection to broker terminated with error:", err)
			}
			log.Println("Stopping service...")
			os.Exit(0)
		}()

		// block to keep the service alive
		<-ctx.Done()
		log.Println("Client terminated connection or keyboard interrupt, shutting down.")

		// retry service again in case of any errors
		time.Sleep(1 * time.Minute)
	}
}

// handler for real time trades
func tradeHandler(t stream.Trade) {
	// construct message via struct
	tradeData := TradeData{
		Exchange: t.Exchange,
		Condition: t.Conditions,
		ID: t.ID,
		Price: t.Price,
		Size: t.Size,
		Symbol: t.Symbol,
		Tape: t.Tape,
		Timestamp: t.Timestamp,
	}

	// marshal struct into JSON
	jsonData, err := json.Marshal(tradeData)
	if err != nil {
		log.Println("Error in marshalling trade data struct to JSON:", err)
		return
	}

	// publish message to the SNS topic
	messageID, err := helpers.PublishSNSMessage(string(jsonData), os.Getenv("DATA_SNS"))

	if err != nil {
		log.Println("Error in publishing live trade data:", err)
		return
	}
	log.Println("Successfully posted live trade data. MessageID:", messageID)

}

// handler for real time quotes
func quoteHandler(q stream.Quote) {
	// construct message via struct
	quoteData := QuoteData{
		AskExchange: q.AskExchange,
		AskPrice: q.AskPrice,
		AskSize: q.AskSize,
		BidExchange: q.BidExchange,
		BidPrice: q.BidPrice,
		BidSize: q.BidSize,
		Conditions: q.Conditions,
		Symbol: q.Symbol,
		Tape: q.Tape,
		Timestamp: q.Timestamp,
	}

	// marshal struct into JSON
	jsonData, err := json.Marshal(quoteData)
	if err != nil {
		log.Println("Error in marshalling trade data struct to JSON:", err)
		return
	}

	// publish message
	messageID, err := helpers.PublishSNSMessage(string(jsonData), os.Getenv("DATA_SNS"))
	if err != nil {
		log.Println("Error in publishing live quote data:", err)
		return
	}
	log.Println("Successfully posted live quote data. MessageID:", messageID)

}

// handler for real time bars
func barHandler(b stream.Bar) {
	// construct message via struct
	barData := BarData{
		Close: b.Close,
		High: b.High,
		Low: b.Low,
		Open: b.Open,
		Symbol: b.Symbol,
		Timestamp: b.Timestamp,
		TradeCount: b.TradeCount,
		VWAP: b.VWAP,
		Volume: b.Volume,
	}

	// marshal struct into JSON
	jsonData, err := json.Marshal(barData)
	if err != nil {
		log.Println("Error in marshalling trade data struct to JSON:", err)
		return
	}

	// publish message
	messageID, err := helpers.PublishSNSMessage(string(jsonData), os.Getenv("DATA_SNS"))

	if err != nil {
		log.Println("Error in publishing live bar data:", err)
		return
	}
	log.Println("Successfully posted live bar data for symbol", b.Symbol, " MessageID:", messageID)
	
}