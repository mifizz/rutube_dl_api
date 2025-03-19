import requests, re, subprocess, ffmpeg

# log modes
# i will update those sometime
logmode_verbose = False
logmode_debug = False

# there will be another log functions
def log(text: str) -> None:
    print(text)
# verbose log
def vlog(text: str) -> None:
    if logmode_verbose:
        print(text)
# debug log
def dlog(text: str) -> None:
    if logmode_debug:
        print(text)

# cut video id from url
def get_video_id(video_url: str) -> str:
    video_id = video_url

    # remove all possible prefixes
    video_id = video_id.removeprefix("http://")
    video_id = video_id.removeprefix("https://")

    video_id = video_id.removeprefix("rutube.ru/")

    video_id = video_id.removeprefix("video")
    # API CAN NOT DOWNLOAD VIDEOS FROM YAPPY
    video_id = video_id.removeprefix("yappy")
    video_id = video_id.removeprefix("shorts")

    video_id = video_id.removeprefix("/")

    # remove tail
    video_id = video_id.split("/")[0]

    return video_id

# returns url for making request to rutube api
def get_api_url(video_id: str) -> str:
    return f"https://rutube.ru/api/play/options/{video_id}"

# makes request to rutube api and returns video info in json
def get_video_json(api_url: str) -> tuple((any, int)):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Firefox/91.0",
        "Accept": "application/json"
    }
    response = requests.get(api_url, headers=headers)

    # all goes ok
    if response.status_code == 200:
        # return json from response
        return (response.json(), 0)
    elif response.status_code == 404:
        # invalid link provided
        log(f"Invalid link!")
        return (None, 404)
    else:
        # something went wrong
        log(f"Can't reach rutube API! Status code: {response.status_code}")
        return (None, response.status_code)

# makes request to master playlist url 
# and returns list of all available streams with elements following this structure:
'''
bandwidth:  BANDWIDTH,
framerate:  FRAMERATE,
codecs:     CODECS,
resolution: RESOLUTION,
url:        STREAM_URL
'''
def get_available_streams(master_url: str) -> tuple((dict, int)):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Firefox/91.0"
    }
    response = requests.get(master_url, headers=headers)
    content = response.text

    # init streams
    streams = []

    # find all streams in response text
    streams_lines = re.findall(r'#EXT-X-STREAM-INF:(.*?)\n(.*?)\n', content, re.DOTALL)

    # format info and put it in streams list
    for info, url in streams_lines:
        bandwidth = re.search(r'BANDWIDTH=(\d+)', info).group(1)
        framerate = re.search(r'FRAME-RATE=(\d+(?:\.\d+)?)', info).group(1)
        codecs = re.search(r'CODECS="([^"]+)"', info).group(1)
        resolution = re.search(r'RESOLUTION=(\d+x\d+)', info).group(1)
        
        # skip if current resolution is already added in list (video mirror)
        if len(streams) > 0 and streams[-1]["resolution"] == resolution:
            continue
        # put new stream in streams :exploding_head:
        streams.append({
            "bandwidth":    bandwidth,
            "framerate":    framerate,
            "codecs":       codecs,
            "resolution":   resolution,
            "url":          url
        })

    # all goes ok
    if response.status_code == 200:
        return (streams, 0)
    # something is not ok
    else:
        log(f"Can't get available streams!\tStatus code: {response.status_code}")
        return (None, response.status_code)

# get vinfo field. path splits by . symbol - for example, "path.to.field" 
# if you want to get video title you need to call this:
# get_vinfo_field(vinfo, "title")
def get_vinfo_field(vinfo: dict, path: str) -> any:
    try:
        # split path to field by dots
        keys = path.split('.')
        
        # recursevely get to field
        current = vinfo
        for key in keys:
            current = current[key]
        
        return current
    except (KeyError, TypeError, IndexError):
        return None

# returns master playlist url (m3u8)
def get_master_playlist(vinfo: dict) -> str:
    return get_vinfo_field(vinfo, path="video_balancer.default")

def download_video(stream: dict) -> int:
    log(f"Downloading video in {in_stream["resolution"]} resolution...")

    # finally download video :tada:
    try:
        video = ffmpeg.input(in_stream["url"])
        video = ffmpeg.output(video, f"{vtitle}.mp4", c="copy", v="error", y=None)
        ffmpeg.run(video)
    except ffmpeg.Error:
        log(f"\nffmpeg error occurred!\tAborting...")
        return 1
    log(f"Saved video in '{vtitle}.mp4'")
    return 0

# execute download if user launched this file directly with python
if __name__ == "__main__":
    # get url from input
    in_url = input("Enter video url: ")

    # get video id first
    # vid stands for video id
    vid = get_video_id(video_url=in_url)
    # log vid
    vlog(f"Video id: '{vid}'")

    # get video info
    vinfo, err_code = get_video_json(api_url=( get_api_url(video_id=vid) ))
    
    # abort if invalid url or any other error
    if err_code > 0:
        vlog(f"Error code > 0\tAborting...")
        exit(1)
    
    # get master playlist
    master_url = get_master_playlist(vinfo)
    dlog(master_url)

    # get video title
    vtitle = get_vinfo_field(vinfo, path="title")
    log(f"Title: '{vtitle}'")

    # get streams
    streams, err_code = get_available_streams(master_url)
    # abort if can't get streams
    if err_code > 0:
        vlog(f"Error code > 0\tAborting...")
        exit(1)

    # print available resolutions
    log("Available resolutions:")
    streams.reverse()
    n: int = 0
    for stream in streams:
        n += 1
        log(f"{n}) {stream["resolution"]}")
    while True:
        # get resolution to download option
        try:
            in_res = input("Choose resolution (default - 1): ")
            if in_res == '':
                in_res = 1
            else:
                in_res = int(in_res)
        except (TypeError):
            log(f"Option must be a number between 1 and {n}")
            continue
        # input number is bigger than n (last available resolution)
        if in_res > n or in_res <= 0:
            log(f"Option must be a number between 1 and {n}")
            continue

        break
    
    # init stream to download
    in_stream = streams[in_res-1]

    if download_video(in_stream) > 0:
        exit(2)
    else:
        exit(0)
