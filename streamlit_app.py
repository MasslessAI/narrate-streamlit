from collections import namedtuple
import math
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, JsCode
import plotly.graph_objects as go
from datetime import datetime
import glob
from collections import defaultdict

st.set_page_config(layout="wide")

st.markdown(
    """
    <style>
    div.row-widget.stRadio > div {
        flex-direction:row;
    }
    </style>
""",
    unsafe_allow_html=True,
)

pd.set_option("display.max_colwidth", None)

st.title("Narrate Lab")

# default subreddit
subreddit = "sneakers"

query_params = st.experimental_get_query_params()
if query_params and "subreddit" in query_params:
    subreddit = query_params["subreddit"][0]

all_reports = [f for f in glob.glob("./reports/*.json")]
subreddit_list = defaultdict(dict)

for report in all_reports:
    splits = report.split('_')
    subreddit_name = None
    if 'report_submission' in report:
        subreddit_name = splits[2]
        subreddit_list[subreddit_name]['report_submission'] = report
    elif 'report_topic_over_time' in report:
        subreddit_name = splits[4]
        subreddit_list[subreddit_name]['report_topic_over_time'] = report
    elif 'report_topic' in report:
        subreddit_name = splits[2]
        subreddit_list[subreddit_name]['report_topic'] = report
    


subreddit_list = [{'subreddit': k, **v } for k, v in subreddit_list.items()]

subreddit = st.selectbox(
    "Select Subreddit",
    [item["subreddit"] for item in subreddit_list],
    index=next(
        idx for idx, item in enumerate(subreddit_list) if item["subreddit"] == subreddit
    ),
)

# load reports
selected_subreddit_item = next(
    item for idx, item in enumerate(subreddit_list) if item["subreddit"] == subreddit
)
df_submissions = pd.read_json(
    selected_subreddit_item["report_submission"]
)

df_topic_info = pd.read_json(
    selected_subreddit_item["report_topic"]
)

df_topic_overtime = pd.read_json(
    selected_subreddit_item["report_topic_over_time"]
)

# find min timestamp and max timestamp
max_timestamp = df_submissions['created_utc'].max()
min_timestamp = df_submissions['created_utc'].min()

st.markdown(
    """
## Data source: [r/{}](https://www.reddit.com//r/{})

** Time Range: {} ~ {} **

- **title**: The title of the post
- **num_comments**: Number of comments in a post
- **score**: The number of upvotes for the post
- **question_category**: A phrase in post title that indicates the post is a question

## How does it work?

Posts are first clustered into similar topics and then sorted by num_comments/score. 

** If the post cannot be assigned to any topic, the post is then labelled Topic #-1 **

""".format(
        subreddit,
        subreddit,
        pd.Timestamp(min_timestamp, unit='s').strftime('%Y-%m'),
        pd.Timestamp(max_timestamp, unit='s').strftime('%Y-%m')
    )
)

def concatenate(tokens):
    return ["_".join(token.split()) for token in tokens]


topic_description_short = [
    "#{} ".format(row["Topic"])
    + " ".join(concatenate(row["Tokens"])[0:5])
    + " (count: {})".format(row["Count"])
    for idx, row in df_topic_info.iterrows()
]

df_topic_info["Topic Description"] = topic_description_short

# sort by topic count in descending order
df_topic_info =  df_topic_info.sort_values(
    by=["Count"], ascending=False
)

topic_id = st.selectbox(
    "Select Topic",
    ['All Topics'] + df_topic_info["Topic"].tolist(),
    format_func=lambda topic_id: df_topic_info.loc[
        df_topic_info["Topic"] == topic_id, "Topic Description"
    ].iloc[0] if topic_id != 'All Topics' else 'All Topics (count {})'.format(len(df_submissions)),
)


if topic_id != 'All Topics':
    df_submissions_by_topic = df_submissions[df_submissions["topic"] == topic_id]
else:
    df_submissions_by_topic = df_submissions

df_submissions_display = df_submissions_by_topic[
    ["title", "num_comments", "score", "title_cat", "permalink"]
]

question_category = sorted(df_submissions_by_topic["title_cat"].unique())
question_category_count = {}
for title_cat in question_category:
    question_category_count[title_cat] = df_submissions_by_topic[
        df_submissions_by_topic["title_cat"] == title_cat
    ].shape[0]

question_category = sorted(
    question_category,
    key=lambda title_cat: question_category_count[title_cat],
    reverse=True,
)
question_category.insert(0, "NONE")
if "NO_WH_WORD" in question_category:
    question_category.remove("NO_WH_WORD")

question_category_selection = st.radio(
    "Filter by question_category",
    question_category,
    format_func=lambda title_cat: "{} (count: {})".format(
        title_cat,
        question_category_count[title_cat]
        if title_cat != "NONE"
        else len(df_submissions_by_topic),
    ),
)

if question_category_selection != "NONE":
    df_submissions_display = df_submissions_display[
        df_submissions_display["title_cat"] == question_category_selection
    ]

df_submissions_display = df_submissions_display.sort_values(
    by=["score"], ascending=False
)


def buildSubmissionTable(df):
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(
        groupable=True, value=True, enableRowGroup=True, aggFunc="sum", editable=True
    )
    gb.configure_side_bar()
    gb.configure_grid_options(domLayout="normal")
    gb.configure_grid_options(
        defaultColDef={
            "flex": 1,
            "resizable": True,
            "sortable": False,
            "autoHeight": True,
        }
    )

    gb.configure_grid_options(
        columnDefs={
            "title": {
                "field": "title",
                "resizable": True,
                "sortable": False,
                "wrapText": True,
                "autoHeight": True,
                "minWidth": 350,
                "cellStyle": {"white-space": "normal", "word-break": "break-word"},
            },
            "num_comments": {
                "headerName": "num_comments",
                "field": "num_comments",
                "flex": 1,
                "resizable": True,
                "sortable": True,
                "maxWidth": 150,
            },
            "score": {
                "headerName": "score",
                "field": "score",
                "flex": 1,
                "resizable": True,
                "sortable": True,
                "maxWidth": 150,
            },
            "question_category": {
                "headerName": "question_category",
                "field": "title_cat",
                "flex": 1,
                "resizable": True,
                "sortable": True,
                "maxWidth": 250,
                "cellStyle": {"white-space": "normal", "word-break": "break-word"},
            },
            "permalink": {
                "headerName": "# comments",
                "field": "permalink",
                "flex": 1,
                "resizable": True,
                "sortable": True,
                "maxWidth": 150,
            },
        }
    )

    # configures last row to use custom styles based on cell's value, injecting JsCode on components front end
    cellsytle_jscode = JsCode(
        """
    function(params) {
        let keyData = params.data.key;
        let newLink = 
        `<a href= https://reddit.com/${params.value} target="_blank">${params.value}</a>`;
        return newLink;
    };
    """
    )
    gb.configure_column("permalink", cellRenderer=cellsytle_jscode)
    # gb.configure_selection("single")
    # gb.configure_selection('single', use_checkbox=True, groupSelectsChildren=True, groupSelectsFiltered=True)
    gridOptions = gb.build()
    grid_response = AgGrid(
        df,
        gridOptions=gridOptions,
        fit_columns_on_grid_load=True,
        data_return_mode=DataReturnMode.AS_INPUT,
        allow_unsafe_jscode=True,
    )


def visualize_topics_over_time(df_topic_info, topics_over_time, width=1250, height=800):
    colors = [
        "#E69F00",
        "#56B4E9",
        "#009E73",
        "#F0E442",
        "#D55E00",
        "#0072B2",
        "#CC79A7",
    ]

    # convert timestamp to year-month
    by_month = pd.to_datetime(topics_over_time['Timestamp']).dt.to_period('M')
    topics_over_time['year_month'] = by_month
    topics_over_time.year_month = topics_over_time.year_month.dt.strftime('%Y-%m')
    del topics_over_time["Timestamp"]
    del topics_over_time["Words"] # topic evolution not needed now 
    # sum by year month
    topics_over_time = topics_over_time.groupby(["Topic", "year_month"], as_index=False)['Frequency'].sum()

    # Select topics
    selected_topics = df_topic_info.Topic.values

    # Prepare data
    data = topics_over_time.loc[topics_over_time.Topic.isin(selected_topics), :]



    # Add traces
    fig = go.Figure()
    for index, topic in enumerate(data.Topic.unique()):
        trace_data = data.loc[data.Topic == topic, :]

        row = df_topic_info.loc[df_topic_info["Topic"] == topic]
        topic_name = "#{} ".format(row["Topic"].iloc[0]) + " ".join(concatenate(row["Tokens"].iloc[0])[0:5])

        #topic_name = topic_name["Topic Description"].iloc[0]
        fig.add_trace(
            go.Scatter(
                x=trace_data.year_month,
                y=trace_data.Frequency,
                line_shape="spline",
                mode="lines+markers",
                marker_color=colors[index % 7],
                name=topic_name,
                hoverlabel=dict(
                    bgcolor="white",
                    font_size=16,
                    font_family="Rockwell",
                    namelength=-1
                ),
                 hovertemplate="<br>".join([
                    "Date: %{x}",
                    "Frequency: %{y}"
                ])
            )
        )

    # Styling of the visualization
    fig.update_xaxes(showgrid=True)
    fig.update_yaxes(showgrid=True)
    fig.update_layout(
        xaxis_tickformat = '%Y-%m',
        yaxis_title="Frequency",
        title={
            "text": "<b>Topics Trends",
            "y": 0.95,
            "x": 0.40,
            "xanchor": "center",
            "yanchor": "top",
            "font": dict(size=22, color="Black"),
        },
        #template="simple_white",
        width=width,
        height=height,
        legend=dict(
            title="<b>Topics  (To show and hide a topic, click the topic name below) </b>",
            xanchor="center",
            yanchor="top",
            y=-0.3,
            x=0.5
        ),
    )
    return fig


# buildTopicTable(df_topic_info)
buildSubmissionTable(df_submissions_display)


st.header("Topic Trends")
st.markdown(
    """
The following figure shows you how often a particular topic has been mentioned in each month in the subreddit.
You can see how the frequency of a topic changes over time. A higher number means that the percentage of posts mentioning that topic are higher.
"""
)

# topic over time
top_k_percent = st.slider(
    "Show Only Most Frequent Topics (by the total number of mentions in the time range)",
    min_value = 10,
    max_value = 100,
    value=20,
    step = 10,
    format='Top %d Percent Most Frequent Topics'
)

df_top_topics = df_topic_info[1: math.floor(top_k_percent * len(df_topic_info) / 100.0)]
topic_over_time_fig = visualize_topics_over_time(df_top_topics, df_topic_overtime)
st.plotly_chart(topic_over_time_fig, use_container_width=True)
