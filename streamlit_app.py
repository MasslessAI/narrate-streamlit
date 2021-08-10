from collections import namedtuple
import altair as alt
import math
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode

pd.set_option('display.max_colwidth', None)
st.set_page_config(layout="wide")
st.title('Narrate Lab')

query_params = st.experimental_get_query_params()
subreddit = query_params['subreddit'][0]

# load reports
df_submissions = pd.read_json('./reports/{}_report_submissions.json'.format(subreddit))
df_topic_info = pd.read_json('./reports/{}_report_topic_info.json'.format(subreddit))

# st.table(df_topic_info)

def concatenate(tokens):
    return ['_'.join(token.split()) for token in tokens]

topic_description_short = [ '#{} '.format(row['Topic']) + ' '.join(concatenate(row['Tokens'])[0:5]) + ' (count: {})'.format(row['Count']) for idx, row in df_topic_info.iterrows()]
df_topic_info['Topic Description'] = topic_description_short

topic_id = st.selectbox(
        'Select Topic',
        df_topic_info['Topic'], format_func = lambda topic_id: df_topic_info.loc[df_topic_info['Topic'] == topic_id, 'Topic Description'].iloc[0])


df_submissions_by_topic = df_submissions[df_submissions['topic'] == topic_id]

df_submissions_display = df_submissions_by_topic[['title', 'num_comments', 'score']]

gb = GridOptionsBuilder.from_dataframe(df_submissions_display)
#gb.configure_grid_options(domLayout='normal')
gb.configure_grid_options(defaultColDef={
    'flex': 1,
    'resizable': True,
    'sortable': False,
    'autoHeight': True,
})

gb.configure_grid_options(columnDefs={'title': {
    'field': 'title',
    'resizable': True,
    'sortable': False,
    'wrapText': True,
    'autoHeight': True,
    'minWidth': 350,
    'cellStyle': {'white-space': 'normal', 'word-break': 'break-word'}
},
'num_comments': {
    'headerName': '# comments',
    'field': 'num_comments',
    'flex': 1,
    'resizable': True,
    'sortable': True,
    'maxWidth': 150,
},
'score': {
    'headerName': 'score',
    'field': 'score',
    'flex': 1,
    'resizable': True,
    'sortable': True,
    'maxWidth': 150,
  }
})

gb.configure_selection('single', use_checkbox=True)
gridOptions = gb.build()
grid_response = AgGrid(df_submissions_display,
    gridOptions=gridOptions,
    fit_columns_on_grid_load=True,
    data_return_mode=DataReturnMode.AS_INPUT, 
)

df = grid_response['data']
selected = grid_response['selected_rows']
selected_df = pd.DataFrame(selected)

selected_df