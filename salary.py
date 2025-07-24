import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(layout="wide")

# State abbreviation mapping
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

career_options = job_salaries_df['Job'].unique()
selected_career = st.selectbox("Select a Career", career_options)

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
working_df['Income to Expenses Ratio'].fillna(0, inplace=True)

# Choropleth map using plotly.graph_objects
fig_map = go.Figure(data=go.Choropleth(
    locations=working_df['Abbreviation'],
    z=working_df['Income to Expenses Ratio'],
    locationmode='USA-states',
    colorscale='Viridis',
    zmin=1,
    zmax=5,
    colorbar_title='Income/Expenses',
    text=working_df['State'],
    hovertemplate="<b>%{text}</b><br>Ratio: %{z:.2f}<extra></extra>",
))

fig_map.update_layout(
    title_text=f'Affordability of Living Expenses vs. {selected_career} Salary by State',
    geo_scope='usa',
    height=600,
    width=1000
)

# Bar charts
def build_bar_chart(df, title):
    return go.Figure(data=go.Bar(
        x=df['State'],
        y=df['Income to Expenses Ratio'],
        marker=dict(color=df['Income to Expenses Ratio'], colorscale='Viridis'),
        hovertemplate="%{x}: %{y:.2f}<extra></extra>"
    )).update_layout(title=title)

top10 = working_df.sort_values('Income to Expenses Ratio', ascending=False).head(10)
bottom10 = working_df.sort_values('Income to Expenses Ratio', ascending=True).head(10)

fig_top = build_bar_chart(top10, "Top 10 States by Income to Expenses Ratio")
fig_bottom = build_bar_chart(bottom10, "Bottom 10 States by Income to Expenses Ratio")

# Display
st.markdown("###  Income-to-Expenses Affordability Map")
st.plotly_chart(fig_map, use_container_width=True)

st.markdown("###  Top & Bottom States by Affordability")
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(fig_top, use_container_width=True)
with col2:
    st.plotly_chart(fig_bottom, use_container_width=True)
