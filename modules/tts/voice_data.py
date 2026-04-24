"""
阿里云TTS音色描述数据
包含所有支持的音色信息及其描述
"""

from typing import Dict, List

# 阿里云TTS音色描述数据
ALIYUN_VOICE_DESCRIPTIONS = {
    "Cherry": {
        "name": "芊悦",
        "gender": "female",
        "description": "阳光积极、亲切自然小姐姐",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "阳光积极",
        "recommended_for": ["日常对话", "产品介绍", "情感表达"],
        "model": "qwen3-tts-flash"
    },
    "Serena": {
        "name": "苏瑶",
        "gender": "female",
        "description": "温柔小姐姐",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "温柔",
        "recommended_for": ["情感表达", "故事讲述", "睡前故事"],
        "model": "qwen3-tts-flash"
    },
    "Ethan": {
        "name": "晨煦",
        "gender": "male",
        "description": "标准普通话，带部分北方口音。阳光、温暖、活力、朝气",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "阳光温暖",
        "recommended_for": ["新闻播报", "教育内容", "正式场合"],
        "model": "qwen3-tts-flash"
    },
    "Chelsie": {
        "name": "千雪",
        "gender": "female",
        "description": "二次元虚拟女友",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "二次元",
        "recommended_for": ["动漫角色", "游戏配音", "虚拟偶像"],
        "model": "qwen3-tts-flash"
    },
    "Momo": {
        "name": "茉兔",
        "gender": "female",
        "description": "撒娇搞怪，逗你开心",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "活泼可爱",
        "recommended_for": ["儿童内容", "娱乐节目", "搞笑视频"],
        "model": "qwen3-tts-flash"
    },
    "Vivian": {
        "name": "十三",
        "gender": "female",
        "description": "拽拽的、可爱的小暴躁",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "个性鲜明",
        "recommended_for": ["角色配音", "个性表达", "短视频"],
        "model": "qwen3-tts-flash"
    },
    "Moon": {
        "name": "月白",
        "gender": "male",
        "description": "率性帅气的月白",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "帅气",
        "recommended_for": ["男性角色", "产品介绍", "正式场合"],
        "model": "qwen3-tts-flash"
    },
    "Maia": {
        "name": "四月",
        "gender": "female",
        "description": "知性与温柔的碰撞",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "知性温柔",
        "recommended_for": ["知识分享", "教育内容", "情感表达"],
        "model": "qwen3-tts-flash"
    },
    "Kai": {
        "name": "凯",
        "gender": "male",
        "description": "耳朵的一场SPA",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "舒适",
        "recommended_for": ["ASMR", "冥想指导", "放松内容"],
        "model": "qwen3-tts-flash"
    },
    "Nofish": {
        "name": "不吃鱼",
        "gender": "male",
        "description": "不会翘舌音的设计师",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "个性",
        "recommended_for": ["角色配音", "个性表达", "短视频"],
        "model": "qwen3-tts-flash"
    },
    "Bella": {
        "name": "萌宝",
        "gender": "female",
        "description": "喝酒不打醉拳的小萝莉",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "可爱",
        "recommended_for": ["儿童内容", "娱乐节目", "搞笑视频"],
        "model": "qwen3-tts-flash"
    },
    "Jennifer": {
        "name": "詹妮弗",
        "gender": "female",
        "description": "品牌级、电影质感般美语女声",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "专业",
        "recommended_for": ["广告配音", "电影解说", "品牌宣传"],
        "model": "qwen3-tts-flash"
    },
    "Ryan": {
        "name": "甜茶",
        "gender": "male",
        "description": "节奏拉满，戏感炸裂，真实与张力共舞",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "戏剧性",
        "recommended_for": ["角色配音", "游戏解说", "影视配音"],
        "model": "qwen3-tts-flash"
    },
    "Katerina": {
        "name": "卡捷琳娜",
        "gender": "female",
        "description": "御姐音色，韵律回味十足",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "御姐",
        "recommended_for": ["角色配音", "情感表达", "高端品牌"],
        "model": "qwen3-tts-flash"
    },
    "Aiden": {
        "name": "艾登",
        "gender": "male",
        "description": "精通厨艺的美语大男孩",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "阳光",
        "recommended_for": ["美食节目", "生活分享", "日常对话"],
        "model": "qwen3-tts-flash"
    },
    "Eldric Sage": {
        "name": "沧明子",
        "gender": "male",
        "description": "沉稳睿智的老者，沧桑如松却心明如镜",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "沉稳睿智",
        "recommended_for": ["历史讲述", "哲学内容", "长者角色"],
        "model": "qwen3-tts-flash"
    },
    "Mia": {
        "name": "乖小妹",
        "gender": "female",
        "description": "温顺如春水，乖巧如初雪",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "温顺乖巧",
        "recommended_for": ["儿童内容", "情感表达", "日常对话"],
        "model": "qwen3-tts-flash"
    },
    "Mochi": {
        "name": "沙小弥",
        "gender": "male",
        "description": "聪明伶俐的小大人，童真未泯却早慧如禅",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "聪明伶俐",
        "recommended_for": ["儿童内容", "教育节目", "角色配音"],
        "model": "qwen3-tts-flash"
    },
    "Bellona": {
        "name": "燕铮莺",
        "gender": "female",
        "description": "声音洪亮，吐字清晰，人物鲜活，听得人热血沸腾；金戈铁马入梦来，字正腔圆间尽显千面人声的江湖",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "洪亮有力",
        "recommended_for": ["历史讲述", "战争题材", "角色配音"],
        "model": "qwen3-tts-flash"
    },
    "Vincent": {
        "name": "田叔",
        "gender": "male",
        "description": "一口独特的沙哑烟嗓，一开口便道尽了千军万马与江湖豪情",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "沙哑烟嗓",
        "recommended_for": ["江湖题材", "历史讲述", "角色配音"],
        "model": "qwen3-tts-flash"
    },
    "Bunny": {
        "name": "萌小姬",
        "gender": "female",
        "description": "“萌属性”爆棚的小萝莉",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "萌系",
        "recommended_for": ["二次元内容", "游戏配音", "虚拟偶像"],
        "model": "qwen3-tts-flash"
    },
    "Neil": {
        "name": "阿闻",
        "gender": "male",
        "description": "平直的基线语调，字正腔圆的咬字发音，这就是最专业的新闻主持人",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "专业新闻",
        "recommended_for": ["新闻播报", "正式场合", "教育内容"],
        "model": "qwen3-tts-flash"
    },
    "Elias": {
        "name": "墨讲师",
        "gender": "female",
        "description": "既保持学科严谨性，又通过叙事技巧将复杂知识转化为可消化的认知模块",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "专业严谨",
        "recommended_for": ["教育内容", "知识分享", "学术讲解"],
        "model": "qwen3-tts-flash"
    },
    "Arthur": {
        "name": "徐大爷",
        "gender": "male",
        "description": "被岁月和旱烟浸泡过的质朴嗓音，不疾不徐地摇开了满村的奇闻异事",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "质朴沧桑",
        "recommended_for": ["故事讲述", "历史内容", "角色配音"],
        "model": "qwen3-tts-flash"
    },
    "Nini": {
        "name": "邻家妹妹",
        "gender": "female",
        "description": "糯米糍一样又软又黏的嗓音，那一声声拉长了的“哥哥”，甜得能把人的骨头都叫酥了",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "甜美软糯",
        "recommended_for": ["情感表达", "日常对话", "角色配音"],
        "model": "qwen3-tts-flash"
    },
    "Ebona": {
        "name": "诡婆婆",
        "gender": "female",
        "description": "她的低语像一把生锈的钥匙，缓慢转动你内心最深处的幽暗角落——那里藏着所有你不敢承认的童年阴影与未知恐惧",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "神秘诡异",
        "recommended_for": ["恐怖内容", "悬疑故事", "角色配音"],
        "model": "qwen3-tts-flash"
    },
    "Seren": {
        "name": "小婉",
        "gender": "female",
        "description": "温和舒缓的声线，助你更快地进入睡眠，晚安，好梦",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "温和舒缓",
        "recommended_for": ["助眠内容", "冥想指导", "放松音频"],
        "model": "qwen3-tts-flash"
    },
    "Pip": {
        "name": "顽屁小孩",
        "gender": "male",
        "description": "调皮捣蛋却充满童真的他来了，这是你记忆中的小新吗",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "调皮童真",
        "recommended_for": ["儿童内容", "搞笑视频", "角色配音"],
        "model": "qwen3-tts-flash"
    },
    "Stella": {
        "name": "少女阿月",
        "gender": "female",
        "description": "平时是甜到发腻的迷糊少女音，但在喊出“代表月亮消灭你”时，瞬间充满不容置疑的爱与正义",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "迷糊少女",
        "recommended_for": ["二次元内容", "角色配音", "动画配音"],
        "model": "qwen3-tts-flash"
    },
    "Bodega": {
        "name": "博德加",
        "gender": "male",
        "description": "热情的西班牙大叔",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "热情",
        "recommended_for": ["西班牙语内容", "角色配音", "旅游节目"],
        "model": "qwen3-tts-flash"
    },
    "Sonrisa": {
        "name": "索尼莎",
        "gender": "female",
        "description": "热情开朗的拉美大姐",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "热情开朗",
        "recommended_for": ["拉美内容", "角色配音", "旅游节目"],
        "model": "qwen3-tts-flash"
    },
    "Alek": {
        "name": "阿列克",
        "gender": "male",
        "description": "一开口，是战斗民族的冷，也是毛呢大衣下的暖",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "冷峻温暖",
        "recommended_for": ["俄语内容", "角色配音", "历史讲述"],
        "model": "qwen3-tts-flash"
    },
    "Dolce": {
        "name": "多尔切",
        "gender": "male",
        "description": "慵懒的意大利大叔",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "慵懒",
        "recommended_for": ["意大利语内容", "角色配音", "生活分享"],
        "model": "qwen3-tts-flash"
    },
    "Sohee": {
        "name": "素熙",
        "gender": "female",
        "description": "温柔开朗，情绪丰富的韩国欧尼",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "温柔开朗",
        "recommended_for": ["韩语内容", "角色配音", "情感表达"],
        "model": "qwen3-tts-flash"
    },
    "Ono Anna": {
        "name": "小野杏",
        "gender": "female",
        "description": "鬼灵精怪的青梅竹马",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "鬼灵精怪",
        "recommended_for": ["日语内容", "角色配音", "二次元内容"],
        "model": "qwen3-tts-flash"
    },
    "Lenn": {
        "name": "莱恩",
        "gender": "male",
        "description": "理性是底色，叛逆藏在细节里——穿西装也听后朋克的德国青年",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "理性叛逆",
        "recommended_for": ["德语内容", "角色配音", "青年文化"],
        "model": "qwen3-tts-flash"
    },
    "Emilien": {
        "name": "埃米尔安",
        "gender": "male",
        "description": "浪漫的法国大哥哥",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "浪漫",
        "recommended_for": ["法语内容", "角色配音", "情感表达"],
        "model": "qwen3-tts-flash"
    },
    "Andre": {
        "name": "安德雷",
        "gender": "male",
        "description": "声音磁性，自然舒服、沉稳男生",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "磁性沉稳",
        "recommended_for": ["情感表达", "正式场合", "角色配音"],
        "model": "qwen3-tts-flash"
    },
    "Radio Gol": {
        "name": "拉迪奥·戈尔",
        "gender": "male",
        "description": "足球诗人Rádio Gol！今天我要用名字为你们解说足球",
        "languages": ["中文", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "激情解说",
        "recommended_for": ["体育解说", "足球内容", "激情表达"],
        "model": "qwen3-tts-flash"
    },
    "Jada": {
        "name": "上海-阿珍",
        "gender": "female",
        "description": "风风火火的沪上阿姐",
        "languages": ["中文（上海话）", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "上海方言",
        "recommended_for": ["上海方言内容", "地方特色", "角色配音"],
        "model": "qwen3-tts-flash"
    },
    "Dylan": {
        "name": "北京-晓东",
        "gender": "male",
        "description": "北京胡同里长大的少年",
        "languages": ["中文（北京话）", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "北京方言",
        "recommended_for": ["北京方言内容", "地方特色", "角色配音"],
        "model": "qwen3-tts-flash"
    },
    "Li": {
        "name": "南京-老李",
        "gender": "male",
        "description": "耐心的瑜伽老师",
        "languages": ["中文（南京话）", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "南京方言",
        "recommended_for": ["南京方言内容", "地方特色", "角色配音"],
        "model": "qwen3-tts-flash"
    },
    "Marcus": {
        "name": "陕西-秦川",
        "gender": "male",
        "description": "面宽话短，心实声沉——老陕的味道",
        "languages": ["中文（陕西话）", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "陕西方言",
        "recommended_for": ["陕西方言内容", "地方特色", "角色配音"],
        "model": "qwen3-tts-flash"
    },
    "Roy": {
        "name": "闽南-阿杰",
        "gender": "male",
        "description": "诙谐直爽、市井活泼的台湾哥仔形象",
        "languages": ["中文（闽南语）", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "闽南方言",
        "recommended_for": ["闽南方言内容", "地方特色", "角色配音"],
        "model": "qwen3-tts-flash"
    },
    "Peter": {
        "name": "天津-李彼得",
        "gender": "male",
        "description": "天津相声，专业捧哏",
        "languages": ["中文（天津话）", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "天津方言",
        "recommended_for": ["天津方言内容", "相声", "角色配音"],
        "model": "qwen3-tts-flash"
    },
    "Sunny": {
        "name": "四川-晴儿",
        "gender": "female",
        "description": "甜到你心里的川妹子",
        "languages": ["中文（四川话）", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "四川方言",
        "recommended_for": ["四川方言内容", "地方特色", "角色配音"],
        "model": "qwen3-tts-flash"
    },
    "Eric": {
        "name": "四川-程川",
        "gender": "male",
        "description": "一个跳脱市井的四川成都男子",
        "languages": ["中文（四川话）", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "四川方言",
        "recommended_for": ["四川方言内容", "地方特色", "角色配音"],
        "model": "qwen3-tts-flash"
    },
    "Rocky": {
        "name": "粤语-阿强",
        "gender": "male",
        "description": "幽默风趣的阿强，在线陪聊",
        "languages": ["中文（粤语）", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "粤语方言",
        "recommended_for": ["粤语方言内容", "地方特色", "角色配音"],
        "model": "qwen3-tts-flash"
    },
    "Kiki": {
        "name": "粤语-阿清",
        "gender": "female",
        "description": "甜美的港妹闺蜜",
        "languages": ["中文（粤语）", "英语", "法语", "德语", "俄语", "意大利语", "西班牙语", "葡萄牙语", "日语", "韩语"],
        "style": "粤语方言",
        "recommended_for": ["粤语方言内容", "地方特色", "角色配音"],
        "model": "qwen3-tts-flash"
    }
}

# 按性别分类的音色
VOICE_BY_GENDER = {
    "female": [name for name, data in ALIYUN_VOICE_DESCRIPTIONS.items() if data["gender"] == "female"],
    "male": [name for name, data in ALIYUN_VOICE_DESCRIPTIONS.items() if data["gender"] == "male"]
}

# 按风格分类的音色
VOICE_BY_STYLE = {
    "阳光积极": ["Cherry", "Ethan"],
    "温柔": ["Serena", "Maia", "Seren"],
    "二次元": ["Chelsie", "Bunny", "Stella"],
    "活泼可爱": ["Momo", "Bella", "Pip"],
    "个性鲜明": ["Vivian", "Nofish"],
    "帅气": ["Moon"],
    "知性温柔": ["Maia"],
    "舒适": ["Kai"],
    "专业": ["Jennifer", "Neil", "Elias"],
    "戏剧性": ["Ryan"],
    "御姐": ["Katerina"],
    "阳光": ["Aiden"],
    "沉稳睿智": ["Eldric Sage"],
    "温顺乖巧": ["Mia"],
    "聪明伶俐": ["Mochi"],
    "洪亮有力": ["Bellona"],
    "沙哑烟嗓": ["Vincent"],
    "萌系": ["Bunny"],
    "质朴沧桑": ["Arthur"],
    "甜美软糯": ["Nini"],
    "神秘诡异": ["Ebona"],
    "温和舒缓": ["Seren"],
    "调皮童真": ["Pip"],
    "迷糊少女": ["Stella"],
    "热情": ["Bodega"],
    "热情开朗": ["Sonrisa"],
    "冷峻温暖": ["Alek"],
    "慵懒": ["Dolce"],
    "温柔开朗": ["Sohee"],
    "鬼灵精怪": ["Ono Anna"],
    "理性叛逆": ["Lenn"],
    "浪漫": ["Emilien"],
    "磁性沉稳": ["Andre"],
    "激情解说": ["Radio Gol"],
    "上海方言": ["Jada"],
    "北京方言": ["Dylan"],
    "南京方言": ["Li"],
    "陕西方言": ["Marcus"],
    "闽南方言": ["Roy"],
    "天津方言": ["Peter"],
    "四川方言": ["Sunny", "Eric"],
    "粤语方言": ["Rocky", "Kiki"]
}

# 支持的语种
SUPPORTED_LANGUAGES = [
    "Chinese", "English", "German", "Italian", "Portuguese", "Spanish", "Japanese", "Korean", "French", "Russian", "Auto"
]

# 支持的模型
SUPPORTED_MODELS = ["qwen3-tts-flash", "qwen-tts"]


def get_voice_description(voice_name: str) -> Dict[str, str]:
    """获取指定音色的描述信息"""
    return ALIYUN_VOICE_DESCRIPTIONS.get(voice_name, {})


def get_voices_by_gender(gender: str) -> List[str]:
    """按性别获取音色列表"""
    return VOICE_BY_GENDER.get(gender, [])


def get_voices_by_style(style: str) -> List[str]:
    """按风格获取音色列表"""
    return VOICE_BY_STYLE.get(style, [])


def search_voices(keyword: str) -> List[Dict[str, str]]:
    """搜索音色（按名称、描述、风格）"""
    results = []
    keyword_lower = keyword.lower()

    for name, data in ALIYUN_VOICE_DESCRIPTIONS.items():
        if (keyword_lower in name.lower() or
            keyword_lower in data["description"].lower() or
            keyword_lower in data["style"].lower() or
            keyword_lower in data["name"].lower()):
            results.append({"name": name, **data})

    return results


def get_all_voices() -> List[Dict[str, str]]:
    """获取所有音色信息"""
    return [{"name": name, **data} for name, data in ALIYUN_VOICE_DESCRIPTIONS.items()]


def get_voice_api_name(voice_name: str) -> str:
    """
    获取音色的API调用名称（英文）

    Args:
        voice_name: 音色名称，可以是英文或中文

    Returns:
        音色的英文API名称，如果找不到则返回原值
    """
    # 如果输入已经是英文API名称，直接返回
    if voice_name in ALIYUN_VOICE_DESCRIPTIONS:
        return voice_name

    # 如果输入是中文名称，查找对应的英文名称
    for api_name, data in ALIYUN_VOICE_DESCRIPTIONS.items():
        if data.get("name") == voice_name:
            return api_name

    # 如果找不到映射，返回原值（保持向后兼容）
    return voice_name
