import modal
import secrets
import time
import urllib.request

# Define a Modal App
app = modal.App("jupyter-sandbox-example")

# Define a custom Docker image with Jupyter and other dependencies
# Install git and other necessary Python packages
image = (
    modal.Image.debian_slim(python_version="3.11") # Using 3.11 as it's the environment you're currently in
    .apt_install("git")
    .pip_install("jupyter~=1.1.0", "h3", "geopandas", "shap")
)

# Define a Modal Secret to store the Jupyter token securely
token = secrets.token_urlsafe(13)
token_secret = modal.Secret.from_dict({"JUPYTER_TOKEN": token})

JUPYTER_PORT = 8888

@app.local_entrypoint()
def main():
    print("🏖️ Creating sandbox...")
    with modal.enable_output():
        # Launch the Modal Sandbox with Jupyter
        sandbox = modal.Sandbox.create(
            "jupyter",
            "notebook",
            "--no-browser",
            "--allow-root",
            "--ip=0.0.0.0",
            f"--port={JUPYTER_PORT}",
            "--NotebookApp.allow_origin='*'",
            "--NotebookApp.allow_remote_access=1",
            f"--NotebookApp.token={token}", # Pass the token directly to Jupyter
            encrypted_ports=[JUPYTER_PORT],
            secrets=[token_secret],
            timeout=5 * 60,  # 5 minutes timeout for idle shutdown
            image=image,
            gpu=None,  # Specify GPU if needed, e.g., "a10g"
            app=app,
        )
    print(f"🏖️ Sandbox ID: {sandbox.object_id}")

    # Get the URL to access the Jupyter server
    # The Sandbox is not publicly accessible until tunnels are created
    jupyter_url = None
    print(f"sandbox.tunnels: {sandbox.tunnels}")
    try:
        tunnels_dict = sandbox.tunnels(JUPYTER_PORT)
        print(f"sandbox.tunnels(JUPYTER_PORT): {tunnels_dict}")
        jupyter_url = f"https://{tunnels_dict[JUPYTER_PORT].host}"
    except Exception as e:
        print(f"Error getting Jupyter URL: {e}")

    if jupyter_url:
        print(f"Jupyter is running at: {jupyter_url}")
        print(f"Token: {token}")
        print("You can open this URL in your browser to access the Jupyter notebook.")
    else:
        print("Failed to retrieve Jupyter URL.")

    # Optional: Wait for the Jupyter server to be ready
    print("Waiting for Jupyter server to be ready...")
    timeout = 60  # seconds
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Check if jupyter_url is set before trying to access it
            if jupyter_url:
                status_url = f"{jupyter_url}/api/status"
                with urllib.request.urlopen(status_url, timeout=5) as response:
                    if response.getcode() == 200:
                        print("Jupyter server is ready!")
                        break
        except urllib.error.URLError:
            pass
        time.sleep(2)
    else:
        print("Jupyter server did not become ready within the timeout.")

    print("\nPress Ctrl+C to terminate the sandbox.")
    # Keep the script running to keep the sandbox alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nTerminating sandbox...")
        sandbox.terminate()
        print("Sandbox terminated.")