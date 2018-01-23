package main

import (
	"flag"
	"log"
	"net/rpc"

	"github.com/streadway/amqp"
	"github.com/vbogretsov/go-amqprpc"
)

var (
	amqpURL string
)

func init() {
	flag.StringVar(
		&amqpURL,
		"amqpurl", "amqp://guest:guest@localhost:5672/",
		"AMQP broker URL")
	flag.Parse()
}

type Args struct {
	A int
	B int
}

type Test struct{}

func (t *Test) Mul(args *Args, reply *int) error {
	*reply = args.A * args.B
	return nil
}

func main() {
	conn, err := amqp.Dial(amqpURL)
	if err != nil {
		log.Fatal(err)
	}

	serverCodec, err := amqprpc.NewServerCodec(conn, "testrpc", amqprpc.Json)
	if err != nil {
		log.Fatal(err)
	}

	rpc.Register(&Test{})
	rpc.ServeCodec(serverCodec)
}
