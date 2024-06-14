package main

import (
	"context"
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"path/filepath"

	"golang.org/x/oauth2/google"
	"google.golang.org/api/drive/v3"
	"google.golang.org/api/option"
)

func main() {
	// Path to your service account key file
	serviceAccountKeyPath := "path/to/your-service-account-key.json"

	// Read the service account key file
	ctx := context.Background()
	b, err := ioutil.ReadFile(serviceAccountKeyPath)
	if err != nil {
		log.Fatalf("Unable to read service account key file: %v", err)
	}

	// Authenticate using the service account key file
	config, err := google.JWTConfigFromJSON(b, drive.DriveReadonlyScope)
	if err != nil {
		log.Fatalf("Unable to parse service account key file to config: %v", err)
	}

	client := config.Client(ctx)

	// Create a new Drive client
	srv, err := drive.NewService(ctx, option.WithHTTPClient(client))
	if err != nil {
		log.Fatalf("Unable to retrieve Drive client: %v", err)
	}

	// Replace with your file ID
	fileId := "your-file-id"

	// Get the file from Google Drive
	file, err := srv.Files.Get(fileId).Download()
	if err != nil {
		log.Fatalf("Unable to retrieve file: %v", err)
	}
	defer file.Body.Close()

	// Create the file in /tmp directory
	tmpFilePath := filepath.Join("/tmp", "downloaded_file")
	tmpFile, err := os.Create(tmpFilePath)
	if err != nil {
		log.Fatalf("Unable to create file in /tmp directory: %v", err)
	}
	defer tmpFile.Close()

	// Write the downloaded file content to the local file
	_, err = ioutil.ReadAll(file.Body)
	if err != nil {
		log.Fatalf("Unable to read file content: %v", err)
	}

	fmt.Printf("File downloaded to %s\n", tmpFilePath)
}
