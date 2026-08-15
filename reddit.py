import json
import datetime
import logging

import asyncpraw
from asyncpraw import models
import requests

import config

logger = logging.getLogger(__name__)

reddit = asyncpraw.Reddit(
    client_id=config.CLIENT_ID,
    client_secret=config.CLIENT_SECRET,
    username=config.USERNAME,
    password=config.PASSWORD,
    user_agent=config.USER_AGENT
)

async def parse_links(post: models.Submission):
    """
    Parse a single post and return a dictionary with relevant information."""
    try:
        post_name = str(post.name)
        post_title = str(post.title)
        post_id = str(post.id)
        post_url = str(post.url)
        post_score = post.score
        logger.info(f"{post_id} post_name={post_name}, post_title={post_title}, post_url={post_url}, post_score={post_score}")

        # if after == post_name:
        #     return None
        
        #TODO save post_url and check duplicates
        
        # this may require extra api requests
        sub_name = str(post.subreddit)
        sub_id = ''
        try:
            logger.debug(f"{post_id} post.subreddit {post.subreddit}")
            r: models.Subreddit = post.subreddit
        except:
            logger.exception(f"{post_id} Probably deleted/removed subreddit {post.subreddit}")
            #return None

        # this may require extra api requests
        user_name = str(post.author)
        user_id = ''
        user_subreddit = None
        try:
            logger.debug(f"{post_id} post.author {post.author}")
            u: models.Redditor = post.author
        except:
            logger.exception(f"{post_id} Probably deleted/removed user {post.author}")

        # Check for non utf8 characters
        post_title_utf8 = post_title.encode('utf8', 'ignore').decode('utf8')
        if len(post_title_utf8) < len(post_title):
            logger.warning(f"{post_id} Warning post has non utf8 characters")

        # Cross post
        if hasattr(post, 'crosspost_parent'):
            if post.crosspost_parent is not None:
                parent = models.Submission(reddit=reddit, id=post.crosspost_parent.split('_')[1])
                await parent.load()
                post = parent

        # download
        direct_url = post_url
        direct_type = ''
        direct_poster = './img/black_pixel.png'

        # First check for imgut or redgifs image
        if ('imgur' in post_url or 'i.redgifs' in post_url) and (post_url.endswith('.jpg') or post_url.endswith('.jpeg')):
            direct_url = './audio/5-seconds-of-silence.mp3'
            direct_type = ''
            direct_poster = post.preview['images'][0]['source']['url']

        # Then jpg
        elif post_url.endswith('.jpg') or post_url.endswith('.jpeg'):
            direct_url = './audio/5-seconds-of-silence.mp3'
            direct_type = ''
            direct_poster = post_url

        # Then png image
        elif post_url.endswith('.png'):
            direct_url = './audio/5-seconds-of-silence.mp3'
            direct_type = ''
            direct_poster = post_url

        # Post link is gallery
        elif hasattr(post, 'is_gallery') and post.is_gallery:
            logger.debug(f"{post_id} vars: {json.dumps(vars(post), default=str)}")
            posts = []
            for data in post.gallery_data['items']:
                media_id = data['media_id']
                media = post.media_metadata[media_id]
                if media['e'] == 'Image':
                    # TODO multiple posts
                    direct_url = './audio/5-seconds-of-silence.mp3'
                    direct_type = ''
                    direct_poster = media['s']['u']
                    logger.info(f"{post_id} direct_poster={direct_poster}")
                    posts.append({
                        'post_id': post_id,
                        'user_id': user_id,
                        'user_name': user_name,
                        'subreddit_id': sub_id,
                        'subreddit_name': sub_name,
                        'post_title': post_title_utf8,
                        'post_url': post_url,
                        'post_created_utc': datetime.datetime.fromtimestamp(int(post.created_utc), datetime.UTC).strftime("%Y-%m-%d %H:%M:%S"),
                        'post_score': post_score,
                        'direct_url': direct_url,
                        'direct_type': direct_type,
                        'direct_poster': direct_poster,
                    })
                elif media['e'] == 'AnimatedImage':
                    # TODO multiple posts
                    direct_url = media['s']['mp4']
                    direct_type = 'video/mp4'
                    direct_poster = './img/black_pixel.png'
                    logger.info(f"{post_id} direct_url={direct_url}")
                    posts.append({
                        'post_id': post_id,
                        'user_id': user_id,
                        'user_name': user_name,
                        'subreddit_id': sub_id,
                        'subreddit_name': sub_name,
                        'post_title': post_title_utf8,
                        'post_url': post_url,
                        'post_created_utc': datetime.datetime.fromtimestamp(int(post.created_utc), datetime.UTC).strftime("%Y-%m-%d %H:%M:%S"),
                        'post_score': post_score,
                        'direct_url': direct_url,
                        'direct_type': direct_type,
                        'direct_poster': direct_poster,
                    })
                else:
                    logger.warning(f"{post_id} Unhandled media type: {media_id}")
            return posts
        
        # get mp4 preview if gif
        elif 'i.redd.it' in post_url and '.gif' in post_url:
            #TODO sometimes gif is image
            logger.debug(f"{post_id} post.preview: {post.preview}")
            direct_url = post.preview['images'][0]['variants']['mp4']['source']['url']
            direct_type = 'video/mp4'
            direct_poster = './img/black_pixel.png'

        elif 'imgur' in post_url and '.gif' in post_url:
            logger.debug(f"{post_id} post.preview: {post.preview}")
            try:
                direct_url = post.preview['images'][0]['variants']['mp4']['source']['url']
                direct_type = 'video/mp4'
                direct_poster = './img/black_pixel.png'
            except:
                direct_url = post.preview['reddit_video_preview']['fallback_url']

        elif 'v.redd.it' in post_url and post.media is not None:
            direct_url = post.media['reddit_video']['dash_url']
            direct_type = 'application/dash+xml'
            direct_poster = './img/black_pixel.png'

        elif 'redgifs' in post_url:
            logger.debug(f"redgifs url: {post_url}")
    
            if 'watch/' in post_url:
                video_id = post_url.split("watch/")[1].split("/")[0].split("#")[0]
            elif 'ifr/' in post_url:
                video_id = post_url.split("ifr/")[1].split("/")[0].split("#")[0]
            else:
                return None
            
            # auth
            auth_url = "https://api.redgifs.com/v2/auth/temporary"
            auth_headers = {
                'referer': 'https://www.redgifs.com/',
                'origin': 'https://www.redgifs.com',
                'content-type': 'application/json',
            }
            # TODO use async session
            auth_response = requests.get(auth_url, headers=auth_headers)
            logger.debug(f"auth_response.status: {auth_response.status_code}")
            if auth_response.status_code != 200:
                return None
            auth_data = auth_response.json()
            auth_response.close()
            logger.debug(f"auth_data.token: {auth_data['token']}")
            
            # api
            api_url = f"https://api.redgifs.com/v2/gifs/{video_id}"
            logger.debug(f"api_url: {api_url}")
            api_headers = {
                'referer': 'https://www.redgifs.com/',
                'origin': 'https://www.redgifs.com',
                'content-type': 'application/json',
                'x-customheader': f'https://www.redgifs.com/watch/{video_id}',
                'authorization': f'Bearer {auth_data['token']}',
            }
            # TODO use async session
            api_response = requests.get(api_url, headers=api_headers)
            logger.debug(f"api_response.status: {api_response.status_code}")
            if api_response.status_code != 200:
                return None
            api_data = api_response.json()
            api_response.close()
            logger.debug(f"api_data.gif.urls: {api_data}")
            direct_url = api_data.get('gif', {}).get('urls', {}).get('sd', '')
            direct_url = api_data.get('gif', {}).get('urls', {}).get('hd', '')

        else:
            logger.warning(f"{post_id} Skipping unknown type: {post_url}")
            return None

        return  [{
            'post_id': post_id,
            'user_id': user_id,
            'user_name': user_name,
            'subreddit_id': sub_id,
            'subreddit_name': sub_name,
            'post_title': post_title_utf8,
            'post_url': post_url,
            'post_created_utc': datetime.datetime.fromtimestamp(int(post.created_utc), datetime.UTC).strftime("%Y-%m-%d %H:%M:%S"),
            'post_score': post_score,
            'direct_url': direct_url,
            'direct_type': direct_type,
            'direct_poster': direct_poster,
        }]

    except:
        logger.exception(f"Post failed: {post} with vars: {json.dumps(vars(post), default=str)}")
        
        return None


#@st.cache_data
async def download_posts(after: str = '', sort: str = 'best', time: str = 'all', multis: str = 'front', limit: int = 100):
    """
    after: t3_link id
    sort: best, hot, new, rising, controversial, top
    t: hour, day, week, month, year, all
    r: subreddit
    m: multireddit
    """

    logger.info(f"after={after}, sort={sort}, time={time}, multis={multis}, limit={limit}")
    params: dict[str, str | int] = {}

    # next page
    if after != '':
        params['after'] = after
    
    # valid sort time
    if time not in ['hour', 'day', 'week', 'month', 'year', 'all']:
        return None
    
    # front
    subreddit = reddit.front
    
    if multis != 'front':
        # multireddit
        l = await reddit.user.multireddits()
        found = False
        for multireddit in l:
            if multis == multireddit.display_name:
                subreddit = multireddit
                found = True
                break
        # Check if multi is found
        if not found:
            return None
        
    generator = []
    if (sort == '' or sort == 'best') and multis == 'front':
        logger.info(f"Generator best")
        generator = subreddit.best(limit=limit, params=params)
    elif sort == 'hot':
        logger.info(f"Generator hot")
        generator = subreddit.hot(limit=limit, params=params)
    elif sort == 'new':
        logger.info(f"Generator new")
        generator = subreddit.new(limit=limit, params=params)
    elif sort == 'rising':
        logger.info(f"Generator rising")
        generator = subreddit.rising(limit=limit, params=params)
    elif sort == 'controversial':
        logger.info(f"Generator controversial")
        generator = subreddit.controversial(limit=limit, params=params, time_filter=time)
    elif sort == 'top':
        logger.info(f"Generator top")
        generator = subreddit.top(limit=limit, params=params, time_filter=time)
    else:
        logger.warning(f"Invalid sort generator: {sort}")
        return None

    # multiple
    posts = []
    async for link in generator:
        new_posts = await parse_links(link)
        if new_posts is not None:
            # TODO yield instead of concat
            # yield new_posts
            # concat list of new posts
            posts.extend(new_posts)
    
    logger.debug(f"posts: {posts}")
    return posts

#@st.cache_data
async def multis():
    """
    after: t3_link id
    sort: best, hot, new, rising, controversial, top
    t: hour, day, week, month, year, all
    r: subreddit
    m: multireddit
    """
    l = await reddit.user.multireddits()
    return [m.display_name for m in l]