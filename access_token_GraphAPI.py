import os

import msal


SCOPES = ["Files.Read", "Sites.Read.All"]


def acquire_access_token() -> str:
	client_id = os.environ.get("MS_GRAPH_CLIENT_ID")
	tenant_id = os.environ.get("MS_GRAPH_TENANT_ID")

	if not client_id or not tenant_id:
		raise RuntimeError(
			"Set MS_GRAPH_CLIENT_ID and MS_GRAPH_TENANT_ID before requesting a token."
		)

	app = msal.PublicClientApplication(
		client_id=client_id,
		authority=f"https://login.microsoftonline.com/{tenant_id}",
	)
	result = app.acquire_token_interactive(scopes=SCOPES)

	if "access_token" not in result:
		message = result.get("error_description") or result.get("error") or "Unknown error"
		raise RuntimeError(f"Microsoft Graph authentication failed: {message}")

	return result["access_token"]


if __name__ == "__main__":
	acquire_access_token()
	print("Microsoft Graph access token acquired successfully.")
