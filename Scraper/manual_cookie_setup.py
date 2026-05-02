import json

def manual_cookie_setup():
    print("MANUAL COOKIE SETUP")
    print("Follow these steps:")
    print("1. Open your regular Chrome/Firefox browser")
    print("2. Go to https://www.grailed.com and log in normally")
    print("3. After logging in press F12 to open DevTools")
    print("4. Go to the Application tab (Chrome) or Storage tab (Firefox)")
    print("5. Click on Cookies then https://www.grailed.com")
    print("6. Find the grailed_jwt cookie")
    print("7. Copy the Value of the grailed_jwt cookie")

    jwt = input("Paste the grailed_jwt cookie value here: ").strip()

    if not jwt:
        print("No JWT provided. Exiting")
        return

    auth_state = {
        "cookies": [
            {
                "name": "grailed_jwt",
                "value": jwt,
                "domain": ".grailed.com",
                "path": "/",
                "expires": -1,
                "httpOnly": False,
                "secure": True,
                "sameSite": "Lax"
            }
        ],
        "origins": []
    }

    print("Optional: For better authentication you can also add:")
    csrf = input("csrf_token (press Enter to skip): ").strip()
    session = input("_grailed_session (press Enter to skip): ").strip()

    if csrf:
        auth_state["cookies"].append({
            "name": "csrf_token",
            "value": csrf,
            "domain": ".grailed.com",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": True,
            "sameSite": "Lax"
        })

    if session:
        auth_state["cookies"].append({
            "name": "_grailed_session",
            "value": session,
            "domain": ".grailed.com",
            "path": "/",
            "expires": -1,
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax"
        })

    with open("grailed_auth.json", "w") as f:
        json.dump(auth_state, f, indent=2)

    print("Authentication saved to grailed_auth.json")
    print("You can now run: python grailed_api_scraper.py")
    print("The scraper will use your saved cookies")


if __name__ == "__main__":
    manual_cookie_setup()
