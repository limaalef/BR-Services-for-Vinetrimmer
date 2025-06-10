import json
import click
from vinetrimmer.objects import AudioTrack, TextTrack, Title, Tracks, VideoTrack
from vinetrimmer.services.BaseService import BaseService
from vinetrimmer.utils.collections import as_list
from datetime import datetime, timedelta
from pathlib import Path
import m3u8, re, os, pickle

class Meliplay(BaseService):
    """
    Service code for Mercado Libre Play (https://play.mercadolivre.com.br/) and other LATAM versions of Mercado Libre Play.

    \b
    Authorization: Cookies 
    Security: FHD@L3/SL2000, doesn't care about releases.
    """

    ALIASES = ["MELI","MELIPLAY","MLPLAY"]

    TITLE_RE = [
        r"^https?://play\.(mercadolivre|mercadolibre)\.(?P<region>[^/]+)(?:/[^/]+)*/(?P<id>[a-f0-9]{32})$",
    ]
    
    REGION_TLD_MAP = {
		"com.ar": "AR",
		"com.br": "BR",
		"cl": "CL",
		"com.co": "CO",
		"com.ec": "EC",
		"com.mx": "MX",
		"com.pe": "PE",
		"com.uy": "UY",
	}

    AUDIO_CODEC_MAP = {
        "AAC": "mp4a",
        "AC3": "ac-3",
        "EC3": "ec-3"
    }
    
    CACHE_DIR = Path(__file__).resolve().parent.parent / "Cache" / "MELI"
    CACHE_FILE = CACHE_DIR / "video_requests.pkl"
    CACHE_EXPIRATION_DAYS = 1

    @staticmethod
    @click.command(name="Meliplay", short_help="https://play.mercadolivre.com.br/")
    @click.argument("title", type=str, required=False)
    @click.option("-s", "--season", is_flag=True, default=False, help="Get all episodes of that episode's season.")
    @click.option("-as", "--all-seasons", is_flag=True, default=False, help="Get all episodes of the all seasons.")
    @click.option("--no-cache", is_flag=True, default=False,
			  help="Disable the use of cached request.")
   
    @click.pass_context
    def cli(ctx, **kwargs):
        return Meliplay(ctx, **kwargs)

    def __init__(self, ctx, title, season, all_seasons, no_cache):
        super().__init__(ctx)
        import yaml
        #Read YAML file
        with open("./vinetrimmer/config/Services/meliplay.yml", 'r') as stream:
            self.config = yaml.safe_load(stream)
        
        self.parse_title_meli(ctx, title)
        self.season = season
        self.allseason = all_seasons
        self.nocache = no_cache
        
        config_region = self.config.get("region")
                
        if self.region == "XX" and not config_region:
            raise self.log.exit(f" Unable to get region from config file")
        elif self.region == "XX" and config_region:
            self.region = config_region
        self.log.info(f" + Region: {self.region}")
        
        self.playready = True if "certificate_chain" in dir(ctx.obj.cdm) else False
        
        cookies = self.session.cookies.get_dict()
        self.session.cookies.update(cookies)
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'
        }
        
    def get_titles(self):
        res_list = []
        
        title_req = self.get_episode(self.title)
        
        if title_req.get("seasons-selector") and self.allseason:
            seasons = self.get_seasons_id_from_episode(title_req)
            
            for season in seasons:
                episodes_list = self.get_episodes_from_season(season)
                
                for episode in episodes_list:
                    res_list.append(self.get_episode(episode))
                
        elif title_req.get("seasons-selector") and self.season:
            episodes_list = self.get_episodes_id(title_req)
            
            for episode in episodes_list:
                res_list.append(self.get_episode(episode))
                
        elif (self.season or self.allseason) and not title_req.get("seasons-selector"):
            self.log.warning(f" + This title isn't a tv series, getting as a movie")
            res_list.append(title_req)
        else:
            res_list.append(title_req)
            self.log.warning(f" + Add -s or --season after url or video id to get all episodes of the season")
            self.log.warning(f" + Add -as or --all-seasons after url or video id to get all episodes from all seasons")
        
        programs = list()
        
        for program in res_list:
            try:
                show_detail = program["player"]["ui"] 
                video_detail = program["player"]["playbackContext"]
                video_detail = program["player"]["playbackContext"]
            except Exception:
                raise self.log.exit("No manifest information.")
            
            try:
                secondaryTitle = show_detail["secondaryTitle"]
            except Exception:
                secondaryTitle = "T0:E0"
                
            title_kwargs = {
                "id_": program["player"]["contentId"],
                "name": show_detail["title"],
                "source": self.ALIASES[0],
                "service_data": program["player"]["playbackContext"]
            }
                
            seasonNumber = secondaryTitle.split(":")[0].strip().replace("T", "")
            episodeNumber = secondaryTitle.split(":")[1].split()[0].strip().replace("E", "")
              
            if seasonNumber and seasonNumber != "0":
                episodeName = secondaryTitle.split(":")[1].split("| ")[1].strip()
                title_kwargs["type_"] = Title.Types.TV
                title_kwargs["season"] = seasonNumber
                title_kwargs["episode"] = episodeNumber
                title_kwargs["episode_name"] = episodeName
            else:
                title_kwargs["type_"] = Title.Types.MOVIE
                
            programs += [Title(**title_kwargs)]
            
        return programs
        
    def get_tracks(self, title):
        vd = title.service_data
        self.manifest_url = vd["sources"]["dash"]
        self.subtitles = vd["subtitles"]
        
        try:
            if self.playready:
                self.lic_url = vd["drm"]["playready"]["serverUrl"]
                self.auth_token = vd["drm"]["playready"]["httpRequestHeaders"]["x-dt-auth-token"]
            else:
                self.lic_url = vd["drm"]["widevine"]["serverUrl"]
                self.auth_token = vd["drm"]["widevine"]["httpRequestHeaders"]["x-dt-auth-token"]
        except:
            pass

        self.log.debug(f" + Downloading Manifest ---> {self.manifest_url}")
        
        if self.manifest_url.find(".m3u8")==-1:
            tracks = Tracks.from_mpd(
                url=self.manifest_url,
                session=self.session,
                source=self.ALIASES[0]
            )
        else:
            tracks = Tracks.from_m3u8(m3u8.load(self.manifest_url), source=self.ALIASES[0])
            if self.acodec:
                tracks.audios = [
                    x for x in tracks.audios if (x.codec or "").split("-")[0] in self.AUDIO_CODEC_MAP[self.acodec]
                ]
            for video in tracks.videos:
                # This is needed to remove weird glitchy NOP data at the end of stream
                video.needs_repack = True
        
        for sub in self.subtitles:
            if sub.get("label") == "No" or sub.get("lang") == "disabled":
                continue
            else:
                tracks.add(TextTrack(
                    id_=sub["label"],
                    source=self.ALIASES[0],
                    url=sub["url"],
                    codec="vtt",
                    language=sub["lang"],
                ), warn_only=True)
        
        return tracks

    def get_chapters(self, title):
        return []

    def certificate(self, **kwargs):
        # TODO: Hardcode the certificate
        return self.license(**kwargs)

    def license(self, challenge, **_):
        cookies = self.session.cookies.get_dict()
        self.session.cookies.update(cookies)
        
        self.session.headers.update({
			"authority": "lic.drmtoday.com",
            "referer": "video_url",
			"x-dt-auth-token": self.auth_token
		})
        
        lic = self.session.post(
            url=self.lic_url,
            headers=self.headers,
            data=challenge  # expects bytes
        )
        return lic.content
                
    def get_seasons_id_from_episode(self, api_res):
        season_list = []
        seasons = api_res["seasons-selector"]["selector"]["props"]["tabs"]
            
        for season in seasons:
            season_list.append(season["value"])
            
        return season_list
                
    def get_episodes_from_season(self, sea_id):
        episode_list = []
        api = f"{self.config["endpoints"][self.region]}/episodes"
        response = self.session.get(
                  api.format(req_type="seasons", title_id=sea_id),
                      headers=self.headers
                  ).json()["props"]["components"]
                  
        for item in response:
            episode_list.append(item["props"]["contentId"])
                          
        return episode_list
    
    def get_episodes_id(self, api_res):
        episode_list = []
        episodes = api_res["seasons-selector"]["carousel"]["props"]["components"]
            
        for episode in episodes:
            episode_list.append(episode["props"]["contentId"])
            
        return episode_list
    
    def get_episode(self, epi_id):
        cache = self.load_cache()
        
        if (self.season or self.allseason) and not self.nocache:
            if epi_id in cache:
                self.log.warning(f" + Getting {epi_id} cached request")
                cached = cache[epi_id]
                if "timestamp" in cached and not self.is_expired(cached["timestamp"]):
                    return cached["data"]
                else:
                    self.log.warning(f" + {epi_id} cached request is old. Getting new")
                    del cache[epi_id]
                    save_cache(cache)
        
        api = self.config["endpoints"][self.region]
        
        try:
            response = self.session.get(
                api.format(req_type="vcp", title_id=epi_id),
                headers=self.headers
            )
                
            response.raise_for_status()
            data = response.json()["components"]
        except (json.JSONDecodeError, KeyError) as e:
            raise self.log.exit(f" - Failed to load title manifest: {response.text}")
            
        cache[epi_id] = {
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        self.save_cache(cache)
        return data
            
    def load_cache(self):
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                self.log.warning("+ Error loading requests cache. Deleting corrupted cache.")
                try:
                    self.CACHE_FILE.unlink()
                except Exception as del_err:
                    raise self.log.exit("+ Unable to clear corrupt requests cache.")
                return {}
        return {}
        
    def save_cache(self, cache):
        with open(self.CACHE_FILE, "wb") as f:
            pickle.dump(cache, f)
            
    def is_expired(self, timestamp_str):
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            return datetime.now() - timestamp > timedelta(days=self.CACHE_EXPIRATION_DAYS)
        except:
            return True
            
    def parse_title_meli(self, ctx, title):
        title = title or ctx.parent.params.get("title")
        if not title:
            self.log.exit(" - No title ID specified")
        if not getattr(self, "TITLE_RE"):
            self.title = title
            return {}
        try:
            for regex in as_list(self.TITLE_RE):
                m = re.search(regex, title)
                if m.group("id"):
                    self.title = m.group("id")
                    result = m.groupdict()
                if m.group("region"):
                    tld = m.group("region")
                    result["region"] = self.REGION_TLD_MAP.get(tld, "XX")
                    self.region = result["region"]
                if self.title or self.region:
                    return result
        except Exception:
            self.log.warning(f" - Unable to parse title ID {title!r}, using as-is")
            self.title = title
            self.region = "XX"