"""Streamlit interface for the AI Movie Recommender."""

import datetime

import streamlit as st

import watchlist as wl
from ai import RecommendationError, build_similar_request, get_recommendations

GENRES = ["Any", "Action", "Comedy", "Drama", "Horror", "Romance", "Sci-Fi", "Thriller", "Animation"]
COUNT_OPTIONS = [3, 5, 10]
EARLIEST_YEAR = 1900
CURRENT_YEAR = datetime.date.today().year


def init_state():
    defaults = {
        "movies": [],
        "error": None,
        "results_title": "Recommended for you",
        "watchlist": [],
        "shown_titles": [],   # every title shown this session, so "more like this" finds new ones
        "last_count": 5,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def render_header():
    st.title("🎬 AI Movie Recommender")
    st.markdown(
        "Tell me what you're in the mood for, and I'll find movies you'll probably enjoy. "
        "Hit **More like this** on any pick to go deeper, and save favourites to your watchlist."
    )


def render_inputs():
    """Draw the input widgets and return the user's choices as a dict."""
    user_request = st.text_area(
        "What kind of movie are you looking for?",
        height=140,
        placeholder=(
            "e.g. A funny action movie with a smart main character, "
            "preferably from the last 10 years."
        ),
    )

    col_count, col_genre = st.columns(2)
    with col_count:
        count = st.selectbox("Number of recommendations", COUNT_OPTIONS, index=1)
    with col_genre:
        genre = st.selectbox("Genre (optional)", GENRES)

    min_year, max_year = None, None
    if st.checkbox("Limit release years"):
        col_min, col_max = st.columns(2)
        with col_min:
            min_year = st.number_input(
                "From year", EARLIEST_YEAR, CURRENT_YEAR, value=CURRENT_YEAR - 10, step=1
            )
        with col_max:
            max_year = st.number_input(
                "To year", EARLIEST_YEAR, CURRENT_YEAR, value=CURRENT_YEAR, step=1
            )

    return {
        "user_request": user_request,
        "count": count,
        "genre": genre,
        "min_year": int(min_year) if min_year else None,
        "max_year": int(max_year) if max_year else None,
    }


def fetch(choices, title, exclude_titles=None):
    """Ask the AI for recommendations and store the outcome in session state."""
    with st.spinner("Finding movies for you..."):
        try:
            movies = get_recommendations(**choices, exclude_titles=exclude_titles)
            st.session_state.movies = movies
            st.session_state.error = None
            st.session_state.results_title = title
            st.session_state.last_count = choices["count"]
            st.session_state.shown_titles += [m["title"] for m in movies]
        except RecommendationError as error:
            st.session_state.error = str(error)
        except Exception:
            # Safety net: never show a raw traceback to the user.
            st.session_state.error = "Something unexpected went wrong. Try again."


def more_like_this(movie):
    """Replace the results with movies similar to `movie`, skipping ones already shown."""
    choices = {
        "user_request": build_similar_request(movie),
        "count": st.session_state.last_count,
        "genre": "Any",
        "min_year": None,
        "max_year": None,
    }
    exclude = [*st.session_state.shown_titles, movie["title"]]
    fetch(choices, f"More like {movie['title']} ({movie['year']})", exclude_titles=exclude)


def render_movie_card(movie, index):
    """Show one recommendation inside a bordered card, with its actions."""
    with st.container(border=True):
        st.markdown(f"### 🎬 {movie['title']}")
        st.markdown(f"**{movie['year']} · {movie['genre']}**")
        st.markdown(f"> {movie['description']}")
        st.markdown("**Why you'll like it:**")
        st.write(movie["why_recommended"])
        st.progress(movie["match_score"] / 100, text=f"**Match:** {movie['match_score']}%")

        col_more, col_save = st.columns(2)
        with col_more:
            if st.button("🔁 More like this", key=f"more_{index}", width="stretch"):
                more_like_this(movie)
                st.rerun()
        with col_save:
            saved = wl.contains(st.session_state.watchlist, movie)
            if st.button(
                "✅ In watchlist" if saved else "➕ Add to watchlist",
                key=f"save_{index}", disabled=saved, width="stretch",
            ):
                st.session_state.watchlist = wl.add(st.session_state.watchlist, movie)
                st.rerun()


def render_watchlist():
    """Sidebar watchlist with remove buttons and a CSV download."""
    with st.sidebar:
        items = st.session_state.watchlist
        st.header(f"📋 Watchlist ({len(items)})")
        if not items:
            st.caption("Movies you add will appear here for this session.")
            return
        for i, movie in enumerate(items):
            col_title, col_remove = st.columns([5, 1])
            col_title.markdown(f"**{movie['title']}** ({movie['year']})  \n{movie['genre']}")
            if col_remove.button("✕", key=f"remove_{i}", help="Remove from watchlist"):
                st.session_state.watchlist = wl.remove(items, movie)
                st.rerun()
        st.download_button(
            "Download watchlist (CSV)", wl.to_csv(items),
            file_name="watchlist.csv", mime="text/csv", width="stretch",
        )
        if st.button("Clear watchlist", width="stretch"):
            st.session_state.watchlist = []
            st.rerun()


def main():
    st.set_page_config(page_title="AI Movie Recommender", page_icon="🎬", layout="centered")
    init_state()
    render_header()
    render_watchlist()
    choices = render_inputs()

    if st.button("Recommend Movies", type="primary", width="stretch"):
        if choices["min_year"] and choices["max_year"] and choices["min_year"] > choices["max_year"]:
            st.warning("\"From year\" must be the same as or earlier than \"To year\".")
        elif not choices["user_request"].strip():
            st.warning("Describe the kind of movie you want first.")
        else:
            st.session_state.movies = []
            fetch(choices, "Recommended for you")

    # Results live in session_state so they survive Streamlit reruns.
    if st.session_state.error:
        st.error(st.session_state.error)

    movies = st.session_state.movies
    if movies:
        st.subheader(st.session_state.results_title)
        if len(movies) < st.session_state.last_count:
            st.caption(
                "Some suggestions were dropped because they were duplicates, already shown, "
                "incomplete, or outside your year range."
            )
        for index, movie in enumerate(movies):
            render_movie_card(movie, index)
        st.caption(
            "Recommendations come from the AI's general knowledge, not a live movie "
            "database. Double-check details like release years before relying on them."
        )


if __name__ == "__main__":
    main()
