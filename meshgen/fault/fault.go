package fault

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"sync"
	"time"
)

type Kind string

const (
	KindLatency Kind = "latency"
	KindError   Kind = "error"
	KindCPUBurn Kind = "cpu_burn"

)

type Spec struct {
	Kind     Kind          `json:"kind"`
	Duration time.Duration `json:"-"`
	DelayMS  int           `json:"delay_ms"`
	Status   int           `json:"status"`
	CPUBurnMS  int         `json:"cpu_burn_ms"`
	// raw duration string from JSON
	DurationRaw string `json:"duration"`
}

type state struct {
	mu sync.RWMutex
	spec *Spec
	until time.Time
}

var global state
func ActiveGauge() int {
        global.mu.RLock()
        defer global.mu.RUnlock()
        if global.spec != nil && time.Now().Before(global.until) {
                return 1
        }
        return 0
}
func MaybeInject(ctx context.Context) error {
        global.mu.RLock()
        spec := global.spec
        until := global.until
        global.mu.RUnlock()
        if spec == nil || time.Now().After(until) {
                return nil
        }
        switch spec.Kind {
        case KindLatency:
                d := time.Duration(spec.DelayMS) * time.Millisecond
                t := time.NewTimer(d)
                defer t.Stop()
                select {
                case <-ctx.Done():
                        return ctx.Err()
                case <-t.C:
                        return nil
                }
        case KindError:
                code := spec.Status
                if code == 0 {
                        code = 503
                }
                return errors.New("injected fault: error")

		case KindCPUBurn:
			deadline := time.Now().Add(time.Duration(spec.CPUBurnMS) * time.Millisecond)
			for time.Now().Before(deadline) {
				select {
					case <-ctx.Done():
						return ctx.Err()
					default:
				}
			}
        }
        return nil
}
func Handler(w http.ResponseWriter, r *http.Request) {
        if r.Method != http.MethodPost {
                http.Error(w, "POST only", http.StatusMethodNotAllowed)
                return
        }
        var spec Spec
        if err := json.NewDecoder(r.Body).Decode(&spec); err != nil {
                http.Error(w, err.Error(), http.StatusBadRequest)
                return
        }
        if spec.DurationRaw == "" {
                spec.DurationRaw = "30s"
        }
        d, err := time.ParseDuration(spec.DurationRaw)
        if err != nil {
                http.Error(w, "bad duration", http.StatusBadRequest)
                return
        }
        spec.Duration = d
        global.mu.Lock()
        global.spec = &spec
        global.until = time.Now().Add(d)
        global.mu.Unlock()
        w.Header().Set("Content-Type", "application/json")
        _ = json.NewEncoder(w).Encode(map[string]any{
                "ok":     true,
                "kind":   spec.Kind,
                "until":  global.until,
        })
}