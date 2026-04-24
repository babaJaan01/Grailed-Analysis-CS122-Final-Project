# Grailed-Analysis-CS122-Final-Project

_**Project Title: Grailed Analysis**_

_**Authors:**_

- Aetius Gular
- Shayaan Tanveer

_**Project Description:**_

The goal of our project is to analyze a sample dataset that represents recently bought items globally from the 2nd-hand resell marketplace known as Grailed. Our analysis will delve into performance across several fields:

1. Categories: looking into how the different array of products perform, if higher volume due to lower price contributes to more revenue that is generated, or do higher priced items that sell due to scarcity perform better.
2. Designers/Brands: does the name of the designer/brand contribute to more sales or higher ctr (click through rate) traction (ie, likes)
3. Price Drops: Does showing a discount on an item make the item more enticing to buy and thus leading to increased sales conversion.
4. Location: Does the region where the item is being bought or sold directly correlate to the type of item or price range of items that are sold.

Our GUI will allow users to delve into even more fields and compare more in depth across different topics pertaining to the Grailed site. This could also be helpful for trend forecasting in different regions. Users will be able to perform their own data analysis and see data visuals at the same time to better analyze the dataset and its trends.

_**Interface Plan:**_

The top will display the filter section that is separated into 3 distinct sections: Graph Type (line, scatter, box, pie chart, histogram, heatmap); Sample Size/Date (when and how much data is going to be displayed; Categories for Comparison/Distribution (Price, Item Type, Discount Rate, Location, Brand, etc.)

_**Data Collection and Storage Plan (Aetius Gular)**_

We will create our dataset by building a webscraper that utilizes Playwright to collect data across new and sold listings that then converts the data that is collected from json to CSV for easier analysis. For each listing we will get key attributes such as price, item type, location, brand, etc. We also plan to have a maintained storage plan for the data (ie raw data, cleaned data, processed data) to keep the different stages of the dataset organized. If necessary we might consider storing the data in a light SQLite database to enable fast querying in integration with our GUI.

_**How to Run**_

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch the GUI
python main.py
```

Place `sold_listings.csv` in the `data/` folder before running. A placeholder file is included so the program runs out of the box.

_**Data Analysis/Visualization Plan (Shayaan Tanveer)**_

We plan to have our data analysis and visualization tools be easily accessible through the GUI. Users will be able to filter, sort, and compare trends between features such as ​​price, location, key words, brands, sizing, etc., and see easy to understand visualizations corresponding to the analysis the user wants.
We will also use various Python libraries that actually help with doing the data analysis and visualization. We will use pandas and numpy for organizing and processing the data with all of their relevant functions. We also plan to use matplotlib and seaborn to get appealing visualizations that help the user and the audience understand what is going on with the data analysis.
