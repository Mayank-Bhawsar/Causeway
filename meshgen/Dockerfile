FROM golang:1.22-alpine AS build
WORKDIR /src
RUN apk add --no-cache git ca-certificates
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /meshgen .

FROM alpine:3.20
RUN apk add --no-cache ca-certificates
COPY --from=build /meshgen /meshgen
EXPOSE 8080
ENTRYPOINT ["/meshgen"]