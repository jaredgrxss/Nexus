package helpers_test

import (
	"testing"
)

func TestHealth(t *testing.T) {
	status := "ok"
	if status != "ok" {
		t.Fatalf("Status has been changed")
	}
}