package main

import (
	    "context"
        "encoding/json"
        "fmt"
        "log"
        "net/http"
        "os"
        "strings"
        "sync/atomic"
        "time"

        "github.com/Mayank-Bhawsar/Causeway/meshgen/fault"
		"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
)

var (
        serviceName = env("SERVICE_NAME", "unknown-svc")
        downstreams = strings.Split(env("DOWNSTREAMS", ""), ",")
        listenAddr  = env("LISTEN_ADDR", ":8080")
        reqCount    atomic.Uint64
)

func env(k, def string) string {
        if v := os.Getenv(k); v != "" {
                return v
        }
        return def
}

func main() {
        // trim empty downstream from Split on ""
        ds := make([]string, 0, len(downstreams))
        for _, d := range downstreams {
                d = strings.TrimSpace(d)
                if d != "" {
                        ds = append(ds, d)
                }
        }
        downstreams = ds

        mux := http.NewServeMux()
        mux.HandleFunc("/health", func(w http.ResponseWriter, _ *http.Request) {
                w.WriteHeader(http.StatusOK)
                _, _ = w.Write([]byte("ok"))
        })
		

        mux.HandleFunc("/metrics", metricsHandler)
        mux.HandleFunc("/admin/fault", fault.Handler)
        mux.HandleFunc("/", handleRequest)

        log.Printf("%s listening on %s downstreams=%v", serviceName, listenAddr, downstreams)
		ctx := context.Background()
		shutdown, err := setupOTel(ctx, serviceName)
		if err != nil {
			log.Printf("otel disabled: %v", err)
		}
		else {
			defer func() { _ = shutdown(context.Background()) }()
		}
		handler := otelhttp.NewHandler(mux, serviceName)
		log.Printf("%s listening on %s downstreams=%v", serviceName, listenAddr, downstreams)
        log.Fatal(http.ListenAndServe(listenAddr, handler))
}

func handleRequest(w http.ResponseWriter, r *http.Request) {
        if err := fault.MaybeInject(r.Context()); err != nil {
                http.Error(w, err.Error(), http.StatusServiceUnavailable)
                return
        }
        reqCount.Add(1)

        // call downstreams (best-effort for now)
        client := &http.Client{
			Timeout:   2 * time.Second,
			Transport: otelhttp.NewTransport(http.DefaultTransport),
		}
        results := map[string]int{}
        for _, d := range downstreams {
                url := d
                if !strings.HasPrefix(url, "http") {
                        url = "http://" + d
                }
                resp, err := client.Get(url + "/")
                if err != nil {
                        results[d] = 0
                        continue
                }
                results[d] = resp.StatusCode
                _ = resp.Body.Close()
        }

        w.Header().Set("Content-Type", "application/json")
        _ = json.NewEncoder(w).Encode(map[string]any{
                "service":     serviceName,
                "downstream":  results,
                "handled_at":  time.Now().UTC(),
        })
}

func metricsHandler(w http.ResponseWriter, _ *http.Request) {
        w.Header().Set("Content-Type", "text/plain; version=0.0.4")
        fmt.Fprintf(w, "# HELP meshgen_requests_total Total requests\n")
        fmt.Fprintf(w, "# TYPE meshgen_requests_total counter\n")
        fmt.Fprintf(w, "meshgen_requests_total{service=%q} %d\n", serviceName, reqCount.Load())
        fmt.Fprintf(w, "# HELP meshgen_fault_active Whether a fault is active\n")
        fmt.Fprintf(w, "# TYPE meshgen_fault_active gauge\n")
        fmt.Fprintf(w, "meshgen_fault_active{service=%q} %d\n", serviceName, fault.ActiveGauge())
}