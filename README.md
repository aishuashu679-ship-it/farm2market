# Smart Farmer Market Price & Buyer Finder

A beginner-friendly Flask + MySQL college project. Farmers can compare sample buyer offers after estimated transportation costs. Buyers can register and add offers.

## Features
- Farmer and buyer registration/login
- Passwords stored as hashes
- Search offers by crop
- Compare gross income, estimated transport cost, and net income
- Sort offers by net income
- Buyer accounts can add offers
- Responsive basic website

## Important demo note
The sample prices, distances, and transport rate are fictional demonstration values. This version does not connect to a live mandi price API, maps, GPS, or a real transport provider. Confirm offers and transport costs before making real decisions.

## 1. Install required software
- Python 3.10 or newer
- MySQL Server (and MySQL Workbench, if desired)
- VS Code

## 2. Create the database
1. Open MySQL Workbench or the MySQL command line.
2. Open and run all statements in `schema.sql`.
3. This creates the `farmer_market_db` database and adds sample buyers/offers.

## 3. Set up Python
Open the project folder in VS Code, then open a terminal in that folder.

Windows:
```bash
py -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

macOS/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 4. Configure MySQL login
Set your MySQL details using environment variables before starting the app.

Windows Command Prompt:
```bat
set DB_HOST=localhost
set DB_USER=root
set DB_PASSWORD=your_actual_mysql_password
set DB_NAME=farmer_market_db
```

PowerShell:
```powershell
$env:DB_HOST="localhost"
$env:DB_USER="root"
$env:DB_PASSWORD="your_actual_mysql_password"
$env:DB_NAME="farmer_market_db"
```

Replace `your_actual_mysql_password` with your own MySQL password. Do not share it or commit it to GitHub.

## 5. Run the website
```bash
python app.py
```
Open `http://127.0.0.1:5000` in your browser.

## 6. Try the demo
- Register as a farmer and log in.
- Open Compare Buyers and search for `Tomato`.
- Enter a quantity, for example 100 kg.
- The demo transport estimate defaults to ₹12 per km for the whole load; change it if you want to test another rate.
- The top result is the offer with the highest estimated net income.
- To add an offer, register another account and choose the `Buyer` role, then open Add Buyer Offer.

## Calculation
- Gross income = buyer price per kg × quantity in kg
- Estimated transport cost = distance in km × transport rate per km for the whole load
- Estimated net income = gross income − estimated transport cost

This is a simplified student-project estimate. Real transport charges may depend on vehicle, load, tolls, loading, unloading, and other factors.

## Troubleshooting
- `Access denied for user`: verify `DB_USER` and `DB_PASSWORD`.
- `Unknown database`: run `schema.sql` first and verify `DB_NAME`.
- `ModuleNotFoundError`: activate the virtual environment and run `pip install -r requirements.txt`.
- Port busy: change the last line of `app.py` to `app.run(debug=True, port=5001)` and open port 5001.

## Suggested future improvements
- Connect an official market-price API or verified data source.
- Use maps/geocoding to estimate route distance rather than manually entered distance.
- Add buyer verification, offer expiry, crop quality/grade, and quantity limits.
- Add tests and use a production server before deploying publicly.
