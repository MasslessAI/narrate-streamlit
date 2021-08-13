from collections import namedtuple
import altair as alt
import math
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, JsCode



st.set_page_config(layout="wide")

st.markdown("""
    <style>
    div.row-widget.stRadio > div {
        flex-direction:row;
    }
    </style>
""", unsafe_allow_html=True)

pd.set_option("display.max_colwidth", None)

st.title("Narrate Lab")

# default subreddit
subreddit = 'startups'

query_params = st.experimental_get_query_params()
if query_params and 'subreddit' in query_params:
    subreddit = query_params['subreddit'][0]

subreddit_list = ['startups', 'cars']

subreddit = st.selectbox(
    "Select Subreddit",
    subreddit_list,
    index = subreddit_list.index(subreddit)
)

st.markdown('''
## Data source: [r/{}](https://www.reddit.com//r/startups)

Time Range: 2018-01-01 ~ 2021-07-19

- **title**: The title of the post
- **num_comments**: Number of comments in a post
- **score**: The number of upvotes for the post
- **question_category**: A phrase in post title that indicates the post is a question

## How does it work?

Posts are first clustered into similar topics and then sorted by num_comments/score.

'''.format(subreddit))


# load reports
df_submissions = pd.read_json("./reports/{}_report_submissions.json".format(subreddit))
df_topic_info = pd.read_json("./reports/{}_report_topic_info.json".format(subreddit))


def concatenate(tokens):
    return ["_".join(token.split()) for token in tokens]


topic_description_short = [
    "#{} ".format(row["Topic"])
    + " ".join(concatenate(row["Tokens"])[0:5])
    + " (count: {})".format(row["Count"])
    for idx, row in df_topic_info.iterrows()
]
df_topic_info["Topic Description"] = topic_description_short

topic_id = st.selectbox(
    "Select Topic",
    df_topic_info["Topic"],
    format_func=lambda topic_id: df_topic_info.loc[
        df_topic_info["Topic"] == topic_id, "Topic Description"
    ].iloc[0],
)


df_submissions_by_topic = df_submissions[df_submissions["topic"] == topic_id]

df_submissions_display = df_submissions_by_topic[
    ["title", "num_comments", "score", "title_cat", "permalink"]
]

question_category = sorted(df_submissions_by_topic['title_cat'].unique());
question_category_count = {}
for title_cat in question_category:
    question_category_count[title_cat] =df_submissions_by_topic[df_submissions_by_topic["title_cat"] == title_cat].shape[0]

question_category = sorted(question_category, key = lambda title_cat: question_category_count[title_cat], reverse=True)
question_category.insert(0, 'NONE')
if 'NO_WH_WORD' in question_category:
    question_category.remove('NO_WH_WORD')

question_category_selection = st.radio(
    "Filter by question_category",
    question_category,
    format_func=lambda title_cat: '{} (count: {})'.format(title_cat, question_category_count[title_cat] if title_cat != 'NONE' else len(df_submissions_by_topic)))

if question_category_selection != 'NONE':
    df_submissions_display = df_submissions_display[df_submissions_display['title_cat'] == question_category_selection]

df_submissions_display = df_submissions_display.sort_values(by=['score'], ascending=False)

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
        allow_unsafe_jscode=True
    )

# buildTopicTable(df_topic_info)
buildSubmissionTable(df_submissions_display)
