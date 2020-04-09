from datetime import datetime
import re
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

date_pattern = re.compile(r"\d{1,2}/\d{1,2}/\d{2}")
def reformat_dates(col_name: str) -> str:
	try:
		return date_pattern.sub(datetime.strptime(col_name, "%m/%d/%y").strftime("%m/%d/%Y"), col_name, count=1)
	except ValueError:
		return col_name

confirmed_cases_url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv"


renamed_columns_map = {
	"Country_Region": "country",
	"Province_State": "location",
	"Lat": "latitude",
	"Long_": "longitude"
}
cols_to_drop = ["country", "latitude", "longitude"]

confirmed_cases_df = (
	pd.read_csv(confirmed_cases_url)
	.rename(columns=renamed_columns_map)
	.rename(columns=reformat_dates)
	.fillna(method="bfill", axis=1)
)

fig = go.Figure()

geo_data_cols = ["country", "location", "latitude", "longitude"]
geo_data_df = confirmed_cases_df[geo_data_cols]
dates_list = (
	confirmed_cases_df.filter(regex=r"(\d{2}/\d{2}/\d{4})", axis=1)
	.columns
	.to_list()
)


cases_by_date = {}
for date in dates_list:
	
	confirmed_cases_day_df = (
		confirmed_cases_df.filter(like=date, axis=1)
		.rename(columns=lambda col: "confirmed_cases")
		.astype("uint32")
	)
	

	cases_df = confirmed_cases_day_df
	cases_df = geo_data_df.join(cases_df) 
	cases_df = cases_df[cases_df["confirmed_cases"] > 0]  # get rid of any rows where there were no cases
	
	cases_by_date[date] = cases_df

fig.data = []
for date, df in cases_by_date.items():
	df["confirmed_cases_norm"] = np.log1p(df["confirmed_cases"])
	df["text"] = (
		date
		+ "<br>"
		+ df["country"]
		+ "<br>"
		+ df["location"]
		+ "<br>Confirmed cases: "
		+ df["confirmed_cases"].astype(str)
	)
	fig.add_trace(
		go.Scattergeo(
			name="",
			lat=df["latitude"],
			lon=df["longitude"],
			visible=False,
			hovertemplate=df["text"],
			showlegend=False,
			marker={
				"size": df["confirmed_cases_norm"] * 100,
				"color": "red",
				"opacity": 0.75,
				"sizemode": "area",
			},
		)
	)

annotation_text_template = "<b>US Totals</b>" \
						   "<br>{date}<br><br>" \
						   "Confirmed cases: {confirmed_cases:,d}<br>" \


annotation_dict = {
	"x": 0.03,
	"y": 0.35,
	"width": 175,
	"height": 110,
	"showarrow": False,
	"text": "",
	"valign": "middle",
	"visible": False,
	"bordercolor": "black",
}

steps = []
for i, data in enumerate(fig.data):
	step = {
		"method": "update",
		"args": [
			{"visible": [False] * len(fig.data)},
			{"annotations": [dict(annotation_dict) for _ in range(len(fig.data))]},
		],
		"label": dates_list[i],
	}


	step["args"][0]["visible"][i] = True
	step["args"][1]["annotations"][i]["visible"] = True

	df = cases_by_date[dates_list[i]]
	confirmed_cases = df["confirmed_cases"].sum()
	step["args"][1]["annotations"][i]["text"] = annotation_text_template.format(
		date=dates_list[i],
		confirmed_cases=confirmed_cases,
	)

	steps.append(step)

sliders = [
	{
		"active": 0,
		"currentvalue": {"prefix": "Date: "},
		"steps": steps,
		"len": 0.9,
		"x": 0.05,
	}
]

first_annotation_dict = {**annotation_dict}
first_annotation_dict.update(
	{
		"visible": True,
		"text": annotation_text_template.format(
			date="01/22/2020", confirmed_cases=1,
		),
	}
)
fig.layout.title = {"text": "Covid-19 US Cases", "x": 0.5}
fig.update_layout(
	height=650,
	margin={"t": 50, "b": 20, "l": 20, "r": 20},
	annotations=[go.layout.Annotation(**first_annotation_dict)],
	sliders=sliders,
)
fig.data[0].visible = True  # set the first data point visible

fig.update_layout(
		geo_scope='usa',
	)

# generate static html plot
fig.update_layout(height=650)  # reduced b/c slider wasn't always visible
fig.write_html("us_covid_cases_static.html")