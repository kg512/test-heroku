import pickle
import re
import urllib
from datetime import datetime, date, timedelta

import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(layout="wide")
st.title("Aaquaverse Passion Maps")
st.markdown("**APM version 1.4**")
main_Section = st.container()
plot_Section = st.container()
community_Section = st.container()
charts_Section = st.container()
BASE_S3_URL = "https://sagemaker-eu-west-1-100701698608.s3.eu-west-1.amazonaws.com/reddit_graph_data"

#graph_date = date(2022,6,30)
graph_date = (datetime.today() - timedelta(days=1))

@st.cache()
def cache_kpe_pickle():
    kpe_topics_path = generate_url(graph_date, 'topics_comments.pkl')
    file = urllib.request.urlopen(kpe_topics_path[0])
    return pickle.load(file)


def generate_url(graph_date: datetime, fname: str):
    failed_dates = []
    errors = []
    for index in range(0, 6):
        cur_date = graph_date - timedelta(days=index)
        url = f"{BASE_S3_URL}/{cur_date.strftime('%Y-%m-%d')}/{fname}"
        if requests.head(url).status_code == 200:
            return (url, cur_date, failed_dates)
        else:
            failed_dates.append(cur_date)
        for failed_date in failed_dates:
            errors.append(failed_date)
    return (None, None, errors)


def paginator(label, topics_df, comments_per_page=3):
    """Lets the user paginate a set of items.
    Parameters
    ----------
    label : str
        The label to display over the pagination widget.
    topics_df : pd.DataFrame
        The dataframe containing the comments to display.
    comments_per_page: int
        The number of comments to display per page.

    Returns
    -------
    pd.DataFrame
        a slice containing the comments to display
    """

    location = st.empty()
    n_pages = (len(topics_df) - 1) // comments_per_page + 1
    page_format_func = lambda i: "Page %s" % i
    if n_pages>1:
        page_number = location.selectbox(f'{label} -- pages: {n_pages}', range(1, n_pages+1), format_func=page_format_func)
    else:
        page_number = 1
    min_index = (page_number-1) * comments_per_page
    max_index = (min_index) + comments_per_page

    return topics_df[min_index:max_index]

@st.cache()
def cache_graph_path(path):
    return path

@st.cache()
def cache_comments_of_subreddit(df):
    return df


comments_kpe_subreddit = cache_kpe_pickle()
kpe_options = list(comments_kpe_subreddit.keys())


with main_Section:
    st.header("View MAGIC Graph Here")
    st.markdown(
        "The MAGIC graph here is mapped out based on the first 400 subreddits for Music, Arts & Entertainment, Games and Interests," +
        "with the addition of some general, geographical and demographic subreddits ")
    st.markdown("**Below is Legend for verticals.**")
    st.image("https://sagemaker-eu-west-1-100701698608.s3.eu-west-1.amazonaws.com/reddit_graph_data/legend.png",
             width=None, use_column_width=None)
    st.markdown("**Each node represents a community and edge represents strength between communities.**")
    st.markdown(f'<p style="color:Red;font-size:20px;">Note</p>', unsafe_allow_html=True)
    st.markdown(
        "The communities for graph are linked by comments. So some subrreddits will not show up if there are no active comments just yet. ")
    st.markdown("**Current graph uses data of past 5 days**")

    st.header("Subreddit topics")
    with st.expander('Explore subreddit topics', expanded=False):

        c1, c2 = st.columns((1, 3))
        with c1:
            option = st.selectbox(
                'Subreddit to explore:',
                [None]+kpe_options)

            if option:
                kps = list(comments_kpe_subreddit[option].keys())[2:]
                if len(kps):
                    st.write('Showing data for:', option)
                    st.write(f'Number of comments used for key phrase extraction in {option} subreddit:',
                             comments_kpe_subreddit[option]['kpe_num_comments'])

                    kp_option = st.selectbox(
                        'keyphrase to explore:',
                    [None]+kps)
                    if kp_option:
                        st.write('Showing data for topic:', kp_option)
                        comments = cache_comments_of_subreddit(comments_kpe_subreddit[option][kp_option])
                        if len(comments):
                            with c2:

                                comments_of_page = paginator('Showing the topics, 3 at the time', comments)
                                comments_data = list(zip(comments_of_page.body, comments_of_page.link_id, comments_of_page.id))
                                for comment in comments_data:
                                    post = f'https://www.reddit.com/r/{option}/comments/{comment[1][3:]}/comment/{comment[2]}'
                                    link = f'[open on reddit.com]({post})'
                                    st.markdown(link)
                                    highlighted_comment = re.sub('(?i)(' + '|'.join(map(re.escape, [kp_option])) + ')', '<span style="color:Red;font-size:20px;">' + r'\1' + '</span>', comment[0])
                                    st.write(highlighted_comment, unsafe_allow_html = True)
                                    st.markdown("""---""")

    c1, c2 = st.columns((3, 1))
    with c2:
        st.header("Graph Parameters")
        with st.form("main_form"):
            confidence_value = st.selectbox(
                "Confidence(%)",
                options=(0.05, 0.10, 0.2),
                help="For an outgoing edge(A—>B) this indicates the probability that given a user is active in the subreddit A " \
                     "then they are also active in B. The higher the minimum confidence, the fewer the edges. The edges will be more certain " \
                     "since they represent higher probabilities. "
            )
            interest_value = st.selectbox(
                "Interest(%)",
                options=(-1.0, 0.0, 0.1, 0.2),
                help="For an outgoing edge(A—>B) this indicates how interesting or surprising this link is. If every user in the dataset " \
                     "is a member of B (extremely popular subreddit) then any association with B will be trivial and uninteresting. " \
                     "If B is a niche subreddit but still has an association with A then their association is interesting. " \
                     "The higher the minimum interest, the fewer the edges. -1 represents connections which are obvious ones"
            )
            min_items_value = st.selectbox(
                "Minimum Items",
                options=(2, 4, 7),
                help="Minimum number of comments made by a user. As the number increases, " \
                     "only users with high activity are included in the graph, and thus the graph would be more reliable."
            )
            node_sizing = st.selectbox(
                'Node sizing',
                options=('Absolute Size', 'Potential Size'),
                help='Determines which attribute is used to show the node size. Absolute Size is number of comments inside reddit.' \
                     'Potential Size takes into account aboslute size plus all incoming edge comments'
            )

            submitted = st.form_submit_button("Load Graph")
            conf = str(confidence_value).replace(".", "_")
            interest = str(interest_value).replace(".", "_")
            items = str(min_items_value).replace(".", "_")
            size = str(node_sizing).lower().replace(" ", "_")
            fname = f"association_graph__min_items_{items}__min_confidence_{conf}__min_interest_{interest}__node_wt_{size}.html"
            (url, plotted_graph_date, errors) = generate_url(graph_date, fname)
    with c1:
        if submitted:
            if len(errors):
                st.error("Failed to load graph for date: " + errors[-1].strftime("%Y-%m-%d"))
            else:
                components.html(urllib.request.urlopen(url).read(), height=900)
        else:
            # This is required to display the graph for the default parameters.
            components.html(urllib.request.urlopen(url).read(), height=900)

with plot_Section:
    plot_Section.header("Compare MAGIC Graph with Community Detection Graph ")
    plot_Section.markdown(
        " You can compare the MAGIC graph with Community Detection Graph here. This is where you will be given filtering options like date selection for each graph and compare them side by side ")
    plot_Section.markdown(
        "**Community Detection graph** is where the algorithm clusters communities together automatically based on edge strength.")
    plot_Section.markdown(
        "As it's an auto-detection, the colour groupings might change every now and then, hence, there will be no legend to map colour to a vertical.")
    plot_Section.markdown(f'<p style="color:Red;font-size:20px;">Note</p>', unsafe_allow_html=True)
    plot_Section.markdown(
        "The communities for both graphs are linked by comments. So some subrreddits will not show up if there are no active comments just yet. ")
    c1, c2 = st.columns((1, 1))

    with c1:
        c1.header("MAGIC Graph")
        st.markdown("**Graph parameters used are below.**")
        st.markdown("Confidence : 0.05")
        st.markdown("Interest : -1")
        st.markdown("Minimum Items: 2")
        st.markdown("Node Sizing : Absolute Size")
        base_file_name = 'association_graph__min_items_2__min_confidence_0_05__min_interest_-1_0__node_wt_absolute_size.html'
        (url, plotted_graph_date, errors) = generate_url(graph_date, base_file_name)
        if len(errors):
            st.error("Failed to load graph for date: " + errors[-1].strftime("%Y-%m-%d"))
        else:
            components.html(urllib.request.urlopen(url).read(), height=900)
    with c2:
        c2.header("Community Detection Graph")
        st.markdown("**Graph parameters used are below.**")
        st.markdown("Confidence : 0.05")
        st.markdown("Interest : -1")
        st.markdown("Minimum Items: 2")
        st.markdown("Node Sizing : Absolute Size")
        base_file_name_communtiy = 'greedy__association_graph__min_items_2__min_confidence_0_05__min_interest_-1_0__node_wt_absolute_size.html'
        (url, plotted_graph_date, errors) = generate_url(graph_date, base_file_name_communtiy)
        if len(errors):
            st.error("Failed to load graph for date: " + errors[-1].strftime("%Y-%m-%d"))
        else:
            components.html(urllib.request.urlopen(url).read(), height=900)
