package helpers

import (
	"log"
	"os"
	"time"
	"github.com/alpacahq/alpaca-trade-api-go/v3/alpaca"
	"github.com/alpacahq/alpaca-trade-api-go/v3/marketdata"
)

/* 
	struct to hold historical data time frame
	for gathering historical data
*/
type HistoricalDataTimeFrame struct {
	Year int
	Month int
	Day int 
}

// reusuable client to handle trade operations
var tradeClient *alpaca.Client
var marketClient *marketdata.Client

// create a new trading client that will be used throughout the specific service
func createOrReturnTradeClient() {
	if tradeClient == nil {
		tradeClient = alpaca.NewClient(alpaca.ClientOpts{
			APIKey: os.Getenv("BROKER_API_KEY"),
			APISecret: os.Getenv("BROKER_SECRET_KEY"),
			BaseURL: os.Getenv("BROKER_URL"),
		})
	}
}

// create a new market client that will be used throughout the specific service
func createOrReturnMarketClient() {
	if marketClient == nil {
		marketClient = marketdata.NewClient(marketdata.ClientOpts{
			APIKey: os.Getenv("BROKER_API_KEY"),
			APISecret: os.Getenv("BROKER_SECRET_KEY"),
		})
	}
}

// check if market has opened for the day or not
func IsMarketOpen() (isMarketOpen bool, Error error) {
	// make sure we have an active broker connection
	createOrReturnTradeClient()
	clock, err := tradeClient.GetClock()
	if err != nil {
		return false, err
	}
	if clock.IsOpen {
		return true, nil
	}
	timeToMarketOpen := int(clock.NextOpen.Sub(clock.Timestamp).Minutes())
	log.Printf("%d minutes until next market open\n", timeToMarketOpen)
	return false, nil 
}

// gather how many minutes till market close
func MinutesTillMarketClose() (minutesTilClose time.Duration, Error error) {
	// make sure we have an active broker connection
	createOrReturnTradeClient()
	clock, err := tradeClient.GetClock()
	if err != nil {
		return -1, err
	}
	return clock.NextClose.Sub(clock.Timestamp), nil
}

/* 
	will execute a market order to be filled 
	at best possible price available immediately
*/
func ExecMarketOrder(order alpaca.PlaceOrderRequest) {
	// make sure we have an active broker connection
}

/* 
	will execute a market order to be filled 
	if and only if price is <= specified price
*/
func ExecLimitOrder() {

}

/*
	will gather historical bar data 
	for a given inputed time frame for 
	a given stock
*/
func GetHistoricalBarData(stock string, startTime HistoricalDataTimeFrame, endTime HistoricalDataTimeFrame) (BarData []marketdata.Bar, Error error) {
	// ensure we have a market client
	createOrReturnMarketClient()
	// gather historical bar data for the given stock
	bars, err := marketClient.GetBars(stock, marketdata.GetBarsRequest{
		TimeFrame: marketdata.OneMin,
		Start: time.Date(startTime.Year, time.Month(startTime.Month), startTime.Day, 0, 0, 0, 0, time.UTC),
		End: time.Date(endTime.Year, time.Month(endTime.Month), endTime.Day, 24, 59, 59, 0, time.UTC),
	})
	// return out error for caller to handle
	if err != nil {
		return nil, err
	}
	return bars, nil
}

/*
	will gather historical quote data 
	for a given inputed time frame for 
	a given stock
*/
func GetHistoricalQuoteData(stock string, limit int, startTime HistoricalDataTimeFrame) (QuoteData []marketdata.Quote, Error error) {
	// ensure we have a market client
	createOrReturnMarketClient()
	quotes, err := marketClient.GetQuotes(stock, marketdata.GetQuotesRequest{
		Start: time.Date(startTime.Year, time.Month(startTime.Month), startTime.Day, 0, 0, 0, 0, time.UTC),
		TotalLimit: limit,
	})
	// return out error for caller to handle
	if err != nil {
		return nil, err
	}
	return quotes, nil
}

/*
	will gather historical trade data 
	for a given inputed time frame for 
	a given stock
*/
func GetHistoricalTradeData(stock string, startTime HistoricalDataTimeFrame, endTime HistoricalDataTimeFrame) (TradeData []marketdata.Trade, Error error) {
	// ensure we have a market client
	createOrReturnMarketClient()
	trades, err := marketClient.GetTrades(stock, marketdata.GetTradesRequest{
		Start: time.Date(startTime.Year, time.Month(startTime.Month), startTime.Day, 0, 0, 0, 0, time.UTC),
		End: time.Date(endTime.Year, time.Month(endTime.Month), endTime.Day, 0, 0, 0, 0, time.UTC),
	})
	// return out error for caller to handle
	if err != nil {
		return nil, err
	}
	return trades, nil
}