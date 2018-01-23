package main

import (
	"flag"
	"log"
	"math/rand"
	"net/rpc"
	"sync"
	"time"

	"github.com/streadway/amqp"
	"github.com/vbogretsov/go-amqprpc"
)

var (
	amqpURL string
)

type Args struct {
	A int
	B int
}

func init() {
	flag.StringVar(
		&amqpURL,
		"amqpurl", "amqp://guest:guest@localhost:5672/",
		"AMQP broker URL")
	flag.Parse()
}

func main() {
	conn, err := amqp.Dial(amqpURL)
	if err != nil {
		log.Fatal(err)
	}

	clientCodec, err := amqprpc.NewClientCodec(conn, "testrpc", amqprpc.Json)
	if err != nil {
		log.Fatal(err)
	}
	defer clientCodec.Close()

	client := rpc.NewClientWithCodec(clientCodec)

	numCalls := 10000
	wg := sync.WaitGroup{}
	wg.Add(numCalls)
	sem := make(chan int, 100)

	t0 := time.Now()
	for i := 0; i < numCalls; i++ {
		sem <- 1
		go func() {
			args := Args{rand.Int() % 100, rand.Int() % 100}
			var result int

			if err := client.Call("Test.Mul", args, &result); err != nil {
				log.Fatal(err)
			}

			if result != args.A*args.B {
				log.Printf("%v * %v != %v", args.A, args.B, result)
				log.Fatal("FAIL")
			}

			wg.Done()
			<-sem
		}()
	}
	wg.Wait()
	log.Printf("SUCCESS, rps: %v", float64(numCalls)/time.Now().Sub(t0).Seconds())
}
