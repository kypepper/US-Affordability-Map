import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_plotly_events import plotly_events

st.set_page_config(layout="wide")  # Make page full width


# State abbreviation mapping (same as your original)
state_mapping = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
    'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA',
    'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
    'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO',
    'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
    'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
    'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
    'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
    'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'
}

# Load your data files here
@st.cache_data
def load_data():
    income_df = pd.read_csv('household_income.csv')
    expenses_df = pd.read_csv('living_expense.csv')
    job_salaries_df = pd.read_csv('job_salaries.csv')
    tax_df = pd.read_csv('tax_rates.csv')
    
    expenses_df[['Grocery', 'Housing', 'Utilities', 'Transportation', 'Health', 'Misc.']] *= 12
    expenses_df['Abbreviation'] = expenses_df['State'].map(state_mapping)
    
    national_avg_income = income_df[income_df['State'] == 'USA']['Household Income'].values[0]
    income_df = income_df[income_df['State'] != 'USA']
    income_df['Percentage Difference from National Average'] = (
        (income_df['Household Income'] - national_avg_income) / national_avg_income
    ) * 100
    
    merged_df = pd.merge(income_df, expenses_df, on='State')
    merged_df['Total Expenses'] = merged_df[['Grocery', 'Housing', 'Utilities', 'Transportation', 'Health', 'Misc.']].sum(axis=1)
    
    tax_df.columns = tax_df.columns.str.strip()
    merged_df = pd.merge(merged_df, tax_df[['State', 'State Tax Rate']], on='State', how='left')
    merged_df['State Tax Rate'] = merged_df['State Tax Rate'].str.rstrip('%').astype('float') / 100
    
    job_salaries_df.columns = job_salaries_df.columns.str.strip()
    job_salaries_df['average_salary'] = job_salaries_df['average_salary'].astype(float)
    job_salaries_df['State'] = 'USA'
    
    return income_df, merged_df, job_salaries_df

income_df, merged_df, job_salaries_df = load_data()

st.title("State Income, Expenses, and Career Salary Analysis")

# Career dropdown
career_options = job_salaries_df['Job'].unique()
selected_career = st.selectbox("Select a Career", career_options)

# Prepare working dataframe based on career selection
working_df = merged_df.copy()

if selected_career == "Average of all Occupations":
    avg_salary = job_salaries_df[job_salaries_df['Job'] == "Average of all Occupations"]['average_salary'].values[0]
    working_df['Adjusted Salary'] = avg_salary
else:
    career_salary = job_salaries_df[job_salaries_df['Job'] == selected_career]
    if career_salary.empty:
        st.error("No data available for this career.")
        st.stop()
    if 'State' in career_salary.columns and career_salary['State'].iloc[0] == 'USA':
        avg_salary = career_salary['average_salary'].iloc[0]
        working_df['Adjusted Salary'] = avg_salary * (1 + working_df['Percentage Difference from National Average'] / 100)
    else:
        career_salary = career_salary[['State', 'average_salary']]
        career_salary.rename(columns={'average_salary': 'Adjusted Salary'}, inplace=True)
        working_df = pd.merge(working_df, career_salary, on='State', how='left')

working_df['Tax Amount'] = working_df['Adjusted Salary'] * working_df['State Tax Rate']
working_df['Adjusted Salary After Tax'] = working_df['Adjusted Salary'] - working_df['Tax Amount']
working_df['Income to Expenses Ratio'] = working_df['Adjusted Salary After Tax'] / working_df['Total Expenses']

# Handle NaN ratios
working_df['Income to Expenses Ratio'].fillna(0, inplace=True)

fixed_color_scale = [
    [0, '#FF4136'],
    [0.25, '#FFDC00'],
    [0.5, '#FFD700'],
    [0.75, '#2ECC40'],
    [1, '#004D40']
]

# Create choropleth map
fig_map = px.choropleth(
    working_df,
    locations='Abbreviation',
    locationmode='USA-states',
    color='Income to Expenses Ratio',
    hover_name='State',
    color_continuous_scale=fixed_color_scale,
    range_color=[1, 5],
    title=f'Affordability of Living Expenses vs. {selected_career} Salary by State',
    labels={'Income to Expenses Ratio': 'Income to Expenses Ratio'},
    scope='usa'
)

fig_map.update_layout(
    coloraxis_colorbar=dict(
        title='Income to Expenses Ratio',
        tickvals=[1, 2, 3, 4, 5],
        ticktext=['1', '2', '3', '4', '5']
    ),
    height=600,
    width=1000
)

# Create top and bottom bar charts
top_bar_chart = px.bar(
    working_df.sort_values(by='Income to Expenses Ratio', ascending=False).head(10),
    x='State', y='Income to Expenses Ratio',
    title='Top 10 States by Income to Expenses Ratio',
    color='Income to Expenses Ratio',
    color_continuous_scale=fixed_color_scale,
    range_color=[1, 5]
)
top_bar_chart.update_layout(coloraxis_showscale=False)

bottom_bar_chart = px.bar(
    working_df.sort_values(by='Income to Expenses Ratio', ascending=True).head(10),
    x='State', y='Income to Expenses Ratio',
    title='Bottom 10 States by Income to Expenses Ratio',
    color='Income to Expenses Ratio',
    color_continuous_scale=fixed_color_scale,
    range_color=[1, 5]
)
bottom_bar_chart.update_layout(coloraxis_showscale=False)

# Layout using Streamlit columns
# Layout: center the map in a wide middle column
st.markdown("### 📍 Income-to-Expenses Affordability Map")

left_space, center_map, right_space = st.columns([1, 5, 1])
with center_map:
    selected_points = plotly_events(fig_map, click_event=True, override_height=600, key='choropleth')

# Bar charts section below the map
st.markdown("### 📊 Top & Bottom States by Affordability")

bar_col1, bar_col2 = st.columns(2)
with bar_col1:
    st.plotly_chart(top_bar_chart, use_container_width=True)

with bar_col2:
    st.plotly_chart(bottom_bar_chart, use_container_width=True)


# Show detailed state info if clicked
if selected_points and len(selected_points) > 0:
    clicked_state = selected_points[0]['location']
    state_data = working_df[working_df['Abbreviation'] == clicked_state].iloc[0]
    st.markdown(f"""
    ### State Information: {state_data['State']}
    - Household Income: ${state_data['Household Income']:,}
    - Total Expenses: ${state_data['Total Expenses']:,}
    - State Tax Rate: {state_data['State Tax Rate'] * 100:.2f}%
    - Income to Expenses Ratio: {state_data['Income to Expenses Ratio']:.2f}
    """)
else:
    st.write("Click on a state in the map to see detailed information.")
