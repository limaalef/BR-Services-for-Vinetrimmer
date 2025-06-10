import json
import click
from vinetrimmer.objects import AudioTrack, TextTrack, Title, Tracks, VideoTrack
from vinetrimmer.services.BaseService import BaseService
from click.core import ParameterSource
import m3u8

class F1tv(BaseService):
    """
    Service code for f1tv pro (https://f1tv.formula1.com/).
    Based on code made by redd.

    \b
    Authorization: Credentials 
    Security: FHD@L3, if is requested. But UHD needs Clearkey, which is not supported
    """

    ALIASES = ["F1TV","F1"]

    TITLE_RE = [
        r"^https?://f1tv\.formula1\.com/detail/(?P<id>\d+)/",
    ]

    AUDIO_CODEC_MAP = {
        "AAC": "mp4a",
        "AC3": "ac-3",
        "EC3": "ec-3"
    }

    @staticmethod
    @click.command(name="F1tv", short_help="https://f1tv.formula1.com/")
    @click.argument("title", type=str, required=False)
   
    @click.pass_context
    def cli(ctx, **kwargs):
        return F1tv(ctx, **kwargs)

    def __init__(self, ctx, title):
        super().__init__(ctx)
        self.parse_title(ctx, title)
        
        import yaml
        #Read YAML file
        with open("./vinetrimmer/config/Services/f1tv.yml", 'r') as stream:
            self.config = yaml.safe_load(stream)

        self.vquality_source = ctx.get_parameter_source("vquality")
        self.vcodec = ctx.parent.params["vcodec"] or "H264"
        self.acodec = ctx.parent.params["acodec"]
        self.quality = ctx.parent.params.get("quality") or 1080
        self.range = ctx.parent.params["range_"] or "SDR"
        
        if self.vquality_source != ParameterSource.COMMANDLINE:
            if self.quality > 1080:
                self.log.debug(" + Setting request device to 'tvos' to be able to get 2160p video track, but it might uses FP which isn't not supported")
                self.vquality = "UHD"
                self.vcodec = "H265"
                self.range = "HDR"
                self.device = self.config["devices"]["tvos"]["DeviceInfo"]
                self.ua = self.config["devices"]["tvos"]["UserAgent"]
                
            elif self.range == "HDR10":
                self.vcodec = "H265"
                self.range = "HDR10"
                self.device = self.config["devices"]["android"]["DeviceInfo"]
                self.ua = self.config["devices"]["android"]["UserAgent"]
                
            else:
                self.device = self.config["devices"]["web"]["DeviceInfo"]
                self.ua = self.config["devices"]["web"]["UserAgent"]
                
        self.region = self.config["region"]
        self.plan = self.config["plan"]

        self.headers = {
            'authority': 'f1tv.formula1.com',
            'entitlementtoken': self.session.cookies.get_dict()["entitlement_token"],
            'x-f1-device-info': self.device,
            'user-agent': self.ua
        }
        
    def get_titles(self):
        params = {
            'contentId': self.title,
            'entitlement': self.plan,
            'homeCountry': self.region, # Replace with your home country / country your account is based on?
        }
        enp1=self.config["endpoints"]["title"]
        
        res = self.session.get(
                enp1.format(title_id=self.title, plan=self.plan, region=self.region),
                headers=self.headers,params=params).json()
        try:
            res
        except json.JSONDecodeError:
            raise self.log.exit(f" - Failed to load title manifest: {res.text}")

        original_language = "en-US"
        fres=res["resultObj"]["containers"][0]["metadata"]
        return Title(
                id_=self.title,
                type_=Title.Types.MOVIE,
                name=(fres["emfAttributes"]["Series"]+" "+fres["emfAttributes"]["Global_Title"]).replace("-"," "),
                 original_lang=original_language,
                source=self.ALIASES[0],
                service_data=res,
            )
        
    def get_tracks(self, title):
        if self.range == "HDR10":
            querystring = { "contentId": self.title, "player": "player_tm" }
        else:
            querystring = { "contentId": self.title }
            
        program_data = self.session.get(
            url=self.config["endpoints"]["tracks"],
            params=querystring,
            headers=self.headers
        ).json()["resultObj"]
        
        try:
            self.lic_url=program_data["laURL"]
        except:
            pass
            
        manifest_url=program_data["url"]
            
        if "manifest.tme" in manifest_url:
            program_data = self.session.get(
                url=manifest_url,
                params=querystring,
                headers=self.headers
            ).json()
            manifest_url=program_data["feeds"][1]["url"]

        self.log.warning(f" + Downloading Manifest ---> {manifest_url}")
        if manifest_url.find("index.m3u8")==-1:
            return Tracks.from_mpd(
                url=manifest_url,
                session=self.session,
                source=self.ALIASES[0]
            )
        else:
            tracks = Tracks.from_m3u8(m3u8.load(manifest_url), source=self.ALIASES[0])
            if self.acodec:
                tracks.audios = [
                    x for x in tracks.audios if (x.codec or "").split("-")[0] in self.AUDIO_CODEC_MAP[self.acodec]
                ]
            for video in tracks.videos:
                # This is needed to remove weird glitchy NOP data at the end of stream
                video.needs_repack = True
            return tracks

    def get_chapters(self, title):
        return []

    def certificate(self, **kwargs):
        # TODO: Hardcode the certificate
        return self.license(**kwargs)

    def license(self, challenge, **_):
        lic = self.session.post(
            url=self.lic_url,
            headers=self.headers,
            data=challenge  # expects bytes
        )
        return lic.content 
