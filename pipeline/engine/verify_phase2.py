from pipeline.engine.downloaders.downloader_factory import DownloaderFactory
import os
import shutil

def test_phase2():
    print("Starting Phase 2 Verification...")
    temp_dir = "temp_downloads"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    try:
        # 1. Test Direct Downloader (using a public direct file or site)
        print("\n--- Testing DirectDownloader ---")
        direct_config = {'rate_limit': 0}
        downloader = DownloaderFactory.get_downloader('direct_download', direct_config)
        
        # Test URL: A small public static file
        test_url = "https://raw.githubusercontent.com/datasets/gdp/master/data/gdp.csv"
        path = downloader.download(test_url, temp_dir)
        
        if os.path.exists(path):
            print(f"SUCCESS: Direct download worked: {path}")
            print(f"File Size: {os.path.getsize(path)} bytes")
            print(f"File Hash: {downloader.get_file_hash(path)}")
        else:
            print("ERROR: Direct download failed to create file.")
            return False

        # 2. Test Browser Renderer (Playwright)
        print("\n--- Testing BrowserRenderer (Playwright) ---")
        browser_config = {'rate_limit': 0, 'wait_condition': {'selector': 'body'}}
        downloader = DownloaderFactory.get_downloader('browser_rendering', browser_config)
        
        # Test URL: A page that requires rendering
        test_url = "https://www.google.com" # Reliable target for rendering test
        path = downloader.download(test_url, temp_dir)
        
        if os.path.exists(path):
            print(f"SUCCESS: Browser rendering worked: {path}")
            # Check if content looks like HTML
            with open(path, 'r', encoding='utf-8') as f:
                snippet = f.read(100)
                print(f"Content Snippet: {snippet}...")
        else:
            print("ERROR: Browser rendering failed to create file.")
            return False

        print("\nPHASE 2 VERIFIED: Universal Acquisition Layer is operational.")
        return True

    except Exception as e:
        print(f"ERROR: Phase 2 verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Keep the files for a moment to let the user see them if they want, 
        # but the script usually cleans up. For now, I'll comment out cleanup.
        # shutil.rmtree(temp_dir)
        pass

if __name__ == "__main__":
    success = test_phase2()
    exit(0 if success else 1)
