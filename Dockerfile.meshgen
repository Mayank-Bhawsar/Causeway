FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod ./
COPY . .
RUN go build -o /meshgen .

FROM alpine:3.20
COPY --from=build /meshgen /meshgen
EXPOSE 8080
ENTRYPOINT ["/meshgen"]