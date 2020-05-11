import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pathlib
import pandas as pd

app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

server = app.server
app.config.suppress_callback_exceptions = True

# Path
BASE_PATH = pathlib.Path(__file__).parent.resolve()
DATA_PATH = BASE_PATH.joinpath("data").resolve()


class Assets:
    @staticmethod
    def readJson(filename):
        import json
        with open(filename) as f:
            config = json.load(f)
        return config

    @staticmethod
    def readCsv(filename):
        import pandas as pd
        return pd.read_csv(filename)
    
    @staticmethod
    def load():
        Assets.CATEGORIES = Assets.readJson('pax-categories.json')
        Assets.PAX_DF = Assets.readCsv('pax_all_agreements_data.csv')
        Assets.FILTERED_DF = Assets.PAX_DF
        Assets.TEXTS = {} # Assets.readJson('pax-texts.json')
        Assets.countIssues()
        
    @staticmethod
    def filterByCategory(pax_category):
        category = int(pax_category) if pax_category else 0
        Assets.SELECTED_CAT =  category
        df = Assets.PAX_DF
        if category == 0:
            Assets.FILTERED_DF = df
        else:
            conditions = []
            for issue in Assets.CATEGORIES[category]['issues']:
                conditions.append('{}>0'.format(issue['value']))
            Assets.FILTERED_DF = df.query('|'.join(conditions))
        return category
            
    @staticmethod
    def getPaxCategory(pax_category):
        cat_number = int(pax_category) if pax_category else 0
        return cat_number, Assets.CATEGORIES[cat_number]["id"]
        
    @staticmethod
    def countIssues():
        df = Assets.PAX_DF
        counters = []
        for category in Assets.CATEGORIES:
            cat_id = category['id']
            if cat_id != 'All':
                for issue in category['issues']:
                    issue_id = issue['value']
                    counts = [issue_id]
                    for provision_type in range(1,4):
                        condition = issue_id + '==' + str(provision_type)
                        counts.append(df.query(condition).shape[0])
                    counters.append(counts)
            col = ['Variable', 'Rhet', 'Con', 'Subs']
            Assets.COUNTERS = pd.DataFrame(counters, columns=col)

        
def get_text(label):
    return Assets.TEXTS.get(label,label)

def get_categories(variable):
    df = Assets.FILTERED_DF
    values = df[variable].unique()
    counts = [df[df[variable]==val].shape[0] for val in values]
    labels = [get_text(value) + ' ' + str(count) 
              for value,count in zip(values,counts)]
    return labels, counts
    
def create_chart(variable, chart_type='bar', title=''):
    labels, values = get_categories(variable)
    if chart_type == 'bar':
        fig = go.Figure(go.Bar(x=values, y=labels, orientation='h'))
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
    elif chart_type == 'pie':
        fig = go.Figure(go.Pie(labels=labels, values=values, title=title))
        fig.update_layout(legend_orientation="h")
    return fig

def create_stacked_bar_chart():
    df = Assets.FILTERED_DF
    category = Assets.SELECTED_CAT
    variables = [var['value'] for var in Assets.CATEGORIES[category]['issues']]
    counters = [[0]*len(variables) for _ in range(3)]
    for i,variable in enumerate(variables):
        for value in df[variable]:
            #value = int(row[variable])
            if value > 0:
                counters[value-1][i]+= 1
    provision_type = ['Rhetorical/Unspecified', 'Concrete', 'Substantial']
    traces = []
    for counter, pt in zip(counters, provision_type):
        traces.append(go.Bar(x=counter, y=variables, name=pt, orientation='h'))
    fig = go.Figure(data=traces, layout=go.Layout(barmode='stack'))
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    return fig

def create_variable_link_bar_chart(variables_to_test):
    var_set = set(variables_to_test)
    df = Assets.FILTERED_DF
    category = Assets.SELECTED_CAT
    variables = [var['value'] for var in Assets.CATEGORIES[category]['issues']
                 if not var['value'] in var_set]
    conditions = '>0&(' + '|'.join([var + '>0' for var in variables]) + ')'
    counts = []
    for var in variables_to_test:
        counts.append(df.query(var + conditions).shape[0])
    fig = go.Figure(go.Bar(x=counts, y=variables_to_test, orientation='h'))
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    return fig
    
            
def description_card():
    """

    :return: A Div containing dashboard title & descriptions.
    """
    pax_url = "[PA-X Peace Agreements Database](https://www.peaceagreements.org/)"
    return html.Div(
        id="description-card",
        children=[
            html.H5("PA-X Peace Agreement Browser"),
            dcc.Markdown(
                "Explore the " + pax_url + " to discover "+
                "trends and topics in peace processes",
            ),
            html.Br()
        ],
    )


def generate_control_card():
    """

    :return: A Div containing controls for graphs.
    """
    return html.Div(
        id="control-card",
        children=[        
            html.P("Select a category of provisions to filter agreements"),
            dcc.Dropdown(
                id="pax-category",
                options=[{"label": cat['group'], "value": str(i)} 
                          for i,cat in enumerate(Assets.CATEGORIES)],
                value="0",
                clearable=False
            ),
            html.Br(),
            html.P("Filters"),
            html.Div(id='div-pax-issues')
        ],
    )


def get_n_agreements():
    df = Assets.FILTERED_DF
    n_agreements = df.shape[0]
    total = Assets.PAX_DF.shape[0]
    pct = round(n_agreements / total * 100)
    return n_agreements, total, pct    

def indicator_card():
    df = Assets.FILTERED_DF
    n_agreements = df.shape[0]
    total = Assets.PAX_DF.shape[0]
    pct = round(n_agreements / total * 100)
    return html.Div(children=[
        html.H5('Agreements Found'),
        html.H1('{} ({} %)'.format(n_agreements, pct), 
                id="n_agreements",
                style={"textAlign": "center"}),
    ])

Assets.load()
app.layout = html.Div(
    id="main",
    children=[
        html.Table([
            html.Tr(
                children=[
                html.Td(style={"verticalAlign": "top", "width": "25%"}, children=[
                    # Left column
                    description_card(), 
                    generate_control_card(),
                    html.Br(),
                    html.Div(style={"text-align": "center"}, children=[
                        html.Button('View Agreements', id="btn-agreements"),
                        html.Br(),
                        html.Br(),
                        html.Label('Powered by', style={"font-size": "10px"}),
                        html.Img(src=app.get_asset_url("plotly_logo.png"),
                                 style={"width": "250px", "height": "40px"}),
                    ])
                ]),
                html.Td(style={"verticalAlign": "top"}, children=[
                    # Facts container
                    html.Div(id="div-pax-facts"),
                    html.Div(
                        children=[html.Img(src=app.get_asset_url("world_map.png"),
                                           style={"width": "900px", "height": "350px"})],
                    ),
                ]),
                html.Td(style={"verticalAlign": "top"}, children=[
                    # Facts container
                    html.Div(children=[
                        indicator_card(),
                        html.H5('Agreements by Region'),
                        dcc.Graph(id="reg-pie")
                    ])
                ]),
            ]),
        ]),
        html.Div(
            style={"columnCount": 3},
            children=[
                html.Div(children=[
                    html.H5(children=html.Div(children="Agreements by Stage")),
                    dcc.Graph(id="stage-barchart"),
                ]),
                html.Div(children=[
                    html.H5(children=html.Div(id="agtp-title")),
                    dcc.Graph(id="agtp-barchart"),
                ]),
                html.Div(children=[
                    html.H5(children=html.Div(id="status-title")),
                    dcc.Graph(id='status-barchart')
                ]),
            ]
        ),
    ],
)


@app.callback(
    Output(component_id='div-pax-issues', component_property='children'),
    [Input(component_id='pax-category', component_property='value')]
)
def update_issues(pax_category):
    category = Assets.filterByCategory(pax_category)
    df = Assets.FILTERED_DF
    n_agreements = df.shape[0]
    total = Assets.PAX_DF.shape[0]
    pct = round(n_agreements / total * 100)
    agt_str = 'Found **{}** agreements of **{}** (**{}**%)'.format(n_agreements, total,pct)
    if category == 0:
        return html.Div(children=dcc.Markdown(agt_str))
    else:
        issues = Assets.CATEGORIES[category]['issues']
        return html.Div([
            dcc.Markdown(agt_str + ' dealing with any of these issues:'),
            dcc.Dropdown(
                    id="pax-issue",
                    options=[issue for issue in issues], 
                    value=[issue['value'] for issue in issues],
                    multi=True,
                    disabled=True
                )
            ])
    
@app.callback(
    Output(component_id='div-pax-facts', component_property='children'),
    [Input(component_id='pax-category', component_property='value')]
)    
def update_facts(pax_category):
    category = int(pax_category) if pax_category else 0
    title = Assets.CATEGORIES[category]['title']
    facts = Assets.CATEGORIES[category]['facts']
    return html.Div([
        html.H5(title),
        html.Ol([html.Li(fact) for fact in facts],
                className="list-numbered", style={"padding": "5px"})
    ])

@app.callback(
    Output(component_id='n_agreements', component_property='children'),
    [Input(component_id='div-pax-facts', component_property='children')]
)    
def update_n_agreements(pax_category):
    n_agreements, total, pct = get_n_agreements()
    return '{} ({} %)'.format(n_agreements, pct)

@app.callback(
    Output(component_id='reg-pie', component_property='figure'),
    [Input(component_id='div-pax-facts', component_property='children')]
)    
def update_region_chart(value):
    return create_chart('Reg', chart_type='pie', title='Agreements by Region')

@app.callback(
    Output(component_id='stage-barchart', component_property='figure'),
    [Input(component_id='div-pax-facts', component_property='children')]
)    
def update_stage_chart(value):
    return create_chart('Stage', chart_type='bar')

@app.callback(
    Output(component_id='agtp-title', component_property='children'),
    [Input(component_id='div-pax-facts', component_property='children')]
)    
def update_agreement_type_title_chart(value):
    if Assets.SELECTED_CAT == 0:
        return 'Agreements by Type'
    else:
        return 'Importance of Provisions'

@app.callback(
    Output(component_id='status-title', component_property='children'),
    [Input(component_id='div-pax-facts', component_property='children')]
)    
def update_status_title_chart(value):
    if Assets.SELECTED_CAT == 0:
        return 'Agreements by Status'
    else:
        return 'Link between SSR and DDR'


@app.callback(
    Output(component_id='agtp-barchart', component_property='figure'),
    [Input(component_id='div-pax-facts', component_property='children')]
)    
def update_agreement_type_chart(value):
    if Assets.SELECTED_CAT == 0:
        return create_chart('Agtp', chart_type='bar')
    else:
        return create_stacked_bar_chart()

@app.callback(
    Output(component_id='status-barchart', component_property='figure'),
    [Input(component_id='div-pax-facts', component_property='children')]
)    
def update_status_chart(value):
    if Assets.SELECTED_CAT == 0:
        return create_chart('Status', chart_type='bar')
    else:
        return create_variable_link_bar_chart(['Ce','SsrDdr'])


# Run the server
if __name__ == "__main__":
    app.run_server(debug=False)
