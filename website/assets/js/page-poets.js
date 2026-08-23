(function () {
  "use strict";
  window.OPTIMIZED_POETS_PAGE = true;

  var poets = window.POETS_INDEX || {};
  var dynastyOrder = ["初唐", "盛唐", "中唐", "晚唐", "唐", "五代", "不详"];
  var chunkSize = 240;
  var visible = chunkSize;
  var currentFilter = "";
  var currentDynasty = "";
  var currentInitial = "";
  var ordered = [];

  // 诗人姓名首字 -> 拼音首字母（由 poets-index.js 预生成）
  var POET_INITIALS = {
    "[": "[", "□": "□", "一": "Y", "丁": "D", "七": "Q", "万": "W", "上": "S", "不": "B", "丘": "Q",
    "东": "D", "严": "Y", "中": "Z", "丰": "F", "临": "L", "丽": "L", "久": "J", "义": "Y", "乐": "L",
    "乔": "Q", "九": "J", "习": "X", "书": "S", "买": "M", "乾": "Q", "了": "L", "予": "Y", "事": "S",
    "二": "E", "于": "Y", "云": "Y", "五": "W", "井": "J", "亚": "Y", "亡": "W", "京": "J", "人": "R",
    "从": "C", "仓": "C", "代": "D", "令": "L", "以": "Y", "仰": "Y", "仲": "Z", "任": "R", "伊": "Y",
    "伍": "W", "伏": "F", "休": "X", "会": "H", "伟": "W", "何": "H", "余": "Y", "佛": "F", "作": "Z",
    "佽": "C", "佳": "J", "使": "S", "来": "L", "侍": "S", "侠": "X", "侣": "L", "俞": "Y", "信": "X",
    "修": "X", "倪": "N", "伦": "L", "俯": "F", "偃": "Y", "假": "J", "偈": "J", "偘": "K", "僧": "S",
    "僊": "X", "僖": "X", "元": "Y", "兆": "Z", "先": "X", "光": "G", "克": "K", "兔": "T", "全": "Q",
    "公": "G", "六": "L", "兰": "L", "共": "G", "关": "G", "兴": "X", "兵": "B", "其": "Q", "典": "D",
    "兹": "Z", "养": "Y", "冀": "J", "冉": "R", "冒": "M", "写": "X", "军": "J", "冠": "G", "冬": "D",
    "冯": "F", "冰": "B", "冲": "C", "况": "K", "冷": "L", "凌": "L", "凝": "N", "几": "J", "凤": "F",
    "刘": "L", "则": "Z", "刚": "G", "利": "L", "刻": "K", "前": "Q", "剑": "J", "剧": "J", "力": "L",
    "功": "G", "务": "W", "动": "D", "助": "Z", "势": "S", "勒": "L", "化": "H", "北": "B", "匡": "K",
    "千": "Q", "升": "S", "半": "B", "华": "H", "卓": "Z", "单": "D", "南": "N", "卜": "B", "卯": "M",
    "印": "Y", "即": "J", "卿": "Q", "历": "L", "厚": "H", "原": "Y", "及": "J", "友": "Y", "双": "S",
    "古": "G", "句": "J", "可": "K", "台": "T", "史": "S", "叶": "Y", "司": "S", "合": "H", "吉": "J",
    "同": "T", "名": "M", "后": "H", "向": "X", "吕": "L", "君": "J", "吴": "W", "吾": "W", "周": "Z",
    "和": "H", "咎": "J", "咏": "Y", "哀": "A", "哈": "H", "唐": "T", "唱": "C", "商": "S", "善": "S",
    "喜": "X", "嘉": "J", "嚣": "X", "四": "S", "回": "H", "因": "Y", "国": "G", "圆": "Y", "圣": "S",
    "在": "Z", "圭": "G", "地": "D", "坤": "K", "垣": "Y", "城": "C", "基": "J", "堂": "T", "堎": "L",
    "堪": "K", "塞": "S", "墨": "M", "夏": "X", "大": "D", "天": "T", "太": "T", "夫": "F", "奇": "Q",
    "奉": "F", "奎": "K", "奚": "X", "女": "N", "好": "H", "如": "R", "妙": "M", "姚": "Y", "姜": "J",
    "姬": "J", "威": "W", "娄": "L", "婆": "P", "婴": "Y", "子": "Z", "孔": "K", "孙": "S", "孝": "X",
    "孟": "M", "季": "J", "孤": "G", "宁": "N", "宇": "Y", "安": "A", "宋": "S", "宏": "H", "宗": "Z",
    "官": "G", "定": "D", "宜": "Y", "宝": "B", "宣": "X", "宪": "X", "宫": "G", "家": "J", "容": "R",
    "寅": "Y", "寇": "K", "富": "F", "寿": "S", "封": "F", "小": "X", "少": "S", "尔": "E", "尚": "S",
    "尹": "Y", "居": "J", "屋": "W", "山": "S", "岑": "C", "岛": "D", "崇": "C", "崔": "C", "嵯": "C",
    "川": "C", "巢": "C", "左": "Z", "巩": "G", "巫": "W", "己": "J", "巴": "B", "巾": "J", "市": "S",
    "布": "B", "帅": "S", "希": "X", "常": "C", "幽": "Y", "庄": "Z", "庆": "Q", "序": "X", "应": "Y",
    "康": "K", "庸": "Y", "庾": "Y", "廉": "L", "廖": "L", "延": "Y", "建": "J", "开": "K", "异": "Y",
    "张": "Z", "强": "Q", "彦": "Y", "彩": "C", "彭": "P", "徐": "X", "徒": "T", "得": "D", "从": "C",
    "御": "Y", "微": "W", "德": "D", "徹": "C", "必": "B", "志": "Z", "忠": "Z", "念": "N", "怀": "H",
    "性": "X", "恒": "H", "恭": "G", "息": "X", "悟": "W", "悦": "Y", "情": "Q", "惟": "W", "惠": "H",
    "想": "X", "慈": "C", "慕": "M", "慧": "H", "懿": "Y", "戎": "R", "成": "C", "戴": "D", "房": "F",
    "所": "S", "扈": "H", "才": "C", "扬": "Y", "承": "C", "振": "Z", "援": "Y", "摩": "M", "撇": "P",
    "攀": "P", "放": "F", "敬": "J", "文": "W", "斋": "Z", "斐": "F", "斑": "B", "方": "F", "於": "Y",
    "无": "W", "日": "R", "旦": "D", "旧": "J", "旨": "Z", "早": "Z", "旭": "X", "时": "S", "明": "M",
    "易": "Y", "星": "X", "春": "C", "昭": "Z", "是": "S", "显": "X", "晋": "J", "晏": "Y", "晓": "X",
    "晚": "W", "景": "J", "智": "Z", "暕": "J", "曲": "Q", "曹": "C", "曾": "Z", "月": "Y", "有": "Y",
    "朋": "P", "朗": "L", "望": "W", "朝": "C", "期": "Q", "木": "M", "未": "W", "本": "B", "朱": "Z",
    "李": "L", "杜": "D", "来": "L", "杨": "Y", "杭": "H", "松": "S", "林": "L", "枚": "M", "果": "G",
    "柏": "B", "某": "M", "查": "Z", "柯": "K", "柳": "L", "柴": "C", "树": "S", "栖": "Q", "栗": "L",
    "根": "G", "桂": "G", "桐": "T", "桑": "S", "梁": "L", "梅": "M", "梓": "Z", "梦": "M", "梵": "F",
    "棕": "Z", "楚": "C", "楼": "L", "槖": "T", "樊": "F", "欧": "O", "欲": "Y", "款": "K", "歌": "G",
    "正": "Z", "武": "W", "段": "D", "殷": "Y", "毋": "W", "每": "M", "毒": "D", "比": "B", "毛": "M",
    "民": "M", "气": "Q", "水": "S", "永": "Y", "求": "Q", "汉": "H", "江": "J", "池": "C", "汤": "T",
    "汪": "W", "沈": "S", "沐": "M", "沙": "S", "治": "Z", "泉": "Q", "法": "F", "波": "B", "泰": "T",
    "洁": "J", "洛": "L", "济": "J", "洪": "H", "洲": "Z", "洽": "Q", "流": "L", "浦": "P", "浪": "L",
    "浮": "F", "海": "H", "涂": "T", "涅": "N", "淮": "H", "深": "S", "清": "Q", "渐": "J", "温": "W",
    "游": "Y", "源": "Y", "溜": "L", "滚": "G", "满": "M", "漠": "M", "漕": "C", "潘": "P", "澹": "D",
    "濮": "P", "濯": "Z", "灵": "L", "炎": "Y", "炭": "T", "炯": "J", "烈": "L", "烦": "F", "照": "Z",
    "熊": "X", "燕": "Y", "爱": "A", "牛": "N", "狄": "D", "独孤": "D", "王": "W", "琴": "Q", "瑜": "Y",
    "瑞": "R", "璇": "X", "甘": "G", "甚": "S", "生": "S", "用": "Y", "田": "T", "由": "Y", "甲": "J",
    "申": "S", "画": "H", "畅": "C", "畏": "W", "留": "L", "畴": "C", "疏": "S", "登": "D", "白": "B",
    "百": "B", "的": "D", "皇": "H", "皮": "P", "益": "Y", "盛": "S", "盩": "Z", "目": "M", "直": "Z",
    "相": "X", "真": "Z", "眠": "M", "瞿": "Q", "知": "Z", "矫": "J", "石": "S", "矶": "J", "破": "P",
    "硕": "S", "碧": "B", "祐": "Y", "祖": "Z", "祝": "Z", "神": "S", "祠": "C", "祥": "X", "禁": "J",
    "禅": "C", "福": "F", "秀": "X", "秉": "B", "秋": "Q", "秦": "Q", "积": "J", "称": "C", "程": "C",
    "穆": "M", "空": "K", "立": "L", "童": "T", "端": "D", "竺": "Z", "符": "F", "第": "D", "简": "J",
    "管": "G", "籍": "J", "米": "M", "粱": "L", "素": "S", "紫": "Z", "繁": "F", "红": "H", "约": "Y",
    "纯": "C", "纱": "S", "纲": "G", "纳": "N", "纵": "Z", "练": "L", "终": "Z", "绍": "S", "经": "J",
    "结": "J", "继": "J", "续": "X", "绰": "C", "维": "W", "缪": "M", "罗": "L", "羊": "Y", "美": "M",
    "羽": "Y", "翁": "W", "翠": "C", "翼": "Y", "老": "L", "耿": "G", "聂": "N", "联": "L", "肃": "S",
    "胡": "H", "胤": "Y", "能": "N", "脩": "X", "腾": "T", "臧": "Z", "自": "Z", "至": "Z", "舒": "S",
    "舜": "S", "舞": "W", "良": "L", "花": "H", "芳": "F", "苏": "S", "苌": "C", "苑": "Y", "苗": "M",
    "苟": "G", "若": "R", "英": "Y", "范": "F", "茅": "M", "茶": "C", "茹": "R", "荆": "J", "草": "C",
    "荐": "J", "荔": "L", "荪": "S", "荷": "H", "荻": "D", "莆": "P", "萧": "X", "萱": "X", "葛": "G",
    "董": "D", "蒋": "J", "蒙": "M", "蒲": "P", "蓝": "L", "蓟": "J", "蓬": "P", "蔚": "W", "蔡": "C",
    "蔺": "L", "薄": "B", "薛": "X", "藏": "C", "虞": "Y", "蜥": "X", "融": "R", "行": "X", "衍": "Y",
    "衣": "Y", "袁": "Y", "裘": "Q", "裴": "P", "褚": "C", "西": "X", "要": "Y", "覃": "T", "覆": "F",
    "见": "J", "观": "G", "解": "J", "言": "Y", "计": "J", "许": "X", "诗": "S", "诸": "Z", "诺": "N",
    "课": "K", "谈": "T", "谋": "M", "谏": "J", "谢": "X", "谬": "M", "谭": "T", "谷": "G", "豆": "D",
    "象": "X", "豪": "H", "貫": "G", "貫休": "G", "賈": "J", "贝": "B", "贤": "X", "贯": "G", "贵": "G",
    "费": "F", "贺": "H", "贾": "J", "赖": "L", "赓": "G", "赵": "Z", "起": "Q", "超": "C", "越": "Y",
    "路": "L", "车": "C", "軒": "X", "輿": "Y", "辛": "X", "辜": "G", "辨": "B", "辰": "C", "达": "D",
    "过": "G", "运": "Y", "远": "Y", "连": "L", "迟": "C", "迪": "D", "迥": "J", "迷": "M", "追": "Z",
    "退": "T", "送": "S", "逆": "N", "透": "T", "通": "T", "逸": "Y", "遂": "S", "道": "D", "邓": "D",
    "邠": "B", "邢": "X", "那": "N", "邱": "Q", "邵": "S", "邹": "Z", "郎": "L", "郑": "Z", "郝": "H",
    "郭": "G", "都": "D", "鄂": "E", "酋": "Q", "酆": "F", "里": "L", "重": "C", "野": "Y", "金": "J",
    "鈐": "Q", "鉅": "J", "鉴": "J", "銑": "X", "钱": "Q", "铁": "T", "铃": "L", "铅": "Q", "铦": "X",
    "铜": "T", "银": "Y", "铸": "Z", "铺": "P", "链": "L", "销": "X", "锁": "S", "锋": "F", "長": "C",
    "长": "Z", "閭": "L", "门": "M", "问": "W", "閻": "Y", "阎": "Y", "阚": "K", "防": "F", "阳": "Y",
    "阴": "Y", "阿": "A", "陆": "L", "陈": "C", "陶": "T", "隆": "L", "隋": "S", "隗": "W", "雍": "Y",
    "雒": "L", "離": "L", "雨": "Y", "雪": "X", "雲": "Y", "霁": "J", "霄": "X", "霆": "T", "霍": "H",
    "青": "Q", "静": "J", "非": "F", "面": "M", "革": "G", "韦": "W", "韩": "H", "音": "Y", "顏": "Y",
    "项": "X", "顺": "S", "顾": "G", "顿": "D", "频": "P", "颖": "Y", "颜": "Y", "飏": "Y", "风": "F",
    "餘": "Y", "馀": "Y", "首": "S", "香": "X", "駱": "L", "马": "M", "骋": "C", "骈": "P", "高": "G",
    "髙": "G", "鬱": "Y", "鬼": "G", "鮑": "B", "鶴": "H", "鷙": "Z", "鹿": "L", "麥": "M", "黄": "H",
    "黎": "L", "黑": "H", "默": "M", "齐": "Q", "龍": "L", "龙": "L"
  };

  function esc(value) {
    return String(value == null ? "" : value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function poetInitial(name) {
    if (!name) return "";
    var first = name.charAt(0);
    return POET_INITIALS[first] || first;
  }

  Object.keys(poets).forEach(function (slug) {
    var poet = poets[slug];
    ordered.push({
      slug: slug,
      poet: poet,
      dynasty: poet[3] || "不详",
      initial: poetInitial(poet[0])
    });
  });
  ordered.sort(function (left, right) {
    var leftDynasty = dynastyOrder.indexOf(left.dynasty);
    var rightDynasty = dynastyOrder.indexOf(right.dynasty);
    if (leftDynasty < 0) leftDynasty = 99;
    if (rightDynasty < 0) rightDynasty = 99;
    if (leftDynasty !== rightDynasty) return leftDynasty - rightDynasty;
    if (right.poet[7] !== left.poet[7]) return right.poet[7] - left.poet[7];
    return left.poet[0].localeCompare(right.poet[0]);
  });

  function matches() {
    return ordered.filter(function (item) {
      if (currentDynasty && item.dynasty !== currentDynasty) return false;
      if (currentInitial && item.initial !== currentInitial) return false;
      if (currentFilter) {
        return item.poet[0].replace(/\s+/g, "").toLowerCase().indexOf(currentFilter) >= 0;
      }
      return true;
    });
  }

  function highlighted(text, q) {
    if (!q) return esc(text);
    var parts = String(text).split(q);
    if (parts.length === 1) return esc(text);
    return parts.map(esc).join('<mark>' + esc(q) + '</mark>');
  }

  function renderCard(item) {
    var poet = item.poet;
    return '<a class="idx-card" href="./poet.html?id=' + encodeURIComponent(item.slug) + '"><div class="seal">' + esc(poet[1]) + '</div><div><div class="nm">' + highlighted(poet[0].replace(/\s+/g, ""), currentFilter) + '</div><div class="n">' + poet[7] + " 首</div></div></a>";
  }

  function render() {
    var all = matches();
    var hasFilters = currentFilter || currentDynasty || currentInitial;
    var shown = hasFilters ? all : all.slice(0, visible);
    var html = "";
    var currentDynastyHeader = "";

    shown.forEach(function (item) {
      if (item.dynasty !== currentDynastyHeader) {
        if (currentDynastyHeader) html += "</div></div>";
        currentDynastyHeader = item.dynasty;
        html += '<div class="idx-group" data-dynasty="' + esc(currentDynastyHeader) + '"><h2>' + esc(currentDynastyHeader) + '</h2><div class="idx-grid">';
      }
      html += renderCard(item);
    });
    if (currentDynastyHeader) html += "</div></div>";

    document.getElementById("idxBody").innerHTML = html;
    document.getElementById("emptyHint").style.display = all.length ? "none" : "block";

    var summary = document.getElementById("summary");
    if (hasFilters) {
      summary.innerHTML = '找到 <span class="num">' + all.length + "</span> 位诗人";
    } else {
      summary.innerHTML = '共 <span class="num">' + all.length + "</span> 位诗人 · 已显示 " + Math.min(visible, all.length) + " 位";
    }

    var more = document.getElementById("poetsMore");
    more.hidden = hasFilters || visible >= all.length;
    if (!more.hidden) more.textContent = "再显示 " + Math.min(chunkSize, all.length - visible) + " 位诗人";

    updateFilterUI();
  }

  function updateFilterUI() {
    var dynastyContainer = document.getElementById("dynastyFilters");
    var initialContainer = document.getElementById("initialFilters");
    if (!dynastyContainer || !initialContainer) return;

    dynastyContainer.querySelectorAll("button").forEach(function (btn) {
      var active = btn.dataset.dynasty === currentDynasty || (btn.dataset.dynasty === "" && !currentDynasty);
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-pressed", String(active));
    });

    initialContainer.querySelectorAll("button").forEach(function (btn) {
      var active = btn.dataset.initial === currentInitial || (btn.dataset.initial === "" && !currentInitial);
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-pressed", String(active));
    });
  }

  function bindFilters() {
    var dynastyContainer = document.getElementById("dynastyFilters");
    var initialContainer = document.getElementById("initialFilters");
    if (!dynastyContainer || !initialContainer) return;

    dynastyContainer.addEventListener("click", function (event) {
      var btn = event.target.closest("button");
      if (!btn) return;
      currentDynasty = btn.dataset.dynasty || "";
      visible = chunkSize;
      render();
      if (currentDynasty) {
        var group = document.querySelector('.idx-group[data-dynasty="' + currentDynasty + '"]');
        if (group) group.scrollIntoView({ behavior: "smooth", block: "start" });
      } else {
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    });

    initialContainer.addEventListener("click", function (event) {
      var btn = event.target.closest("button");
      if (!btn) return;
      currentInitial = btn.dataset.initial || "";
      visible = chunkSize;
      render();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  var timer = null;
  document.getElementById("searchInput").addEventListener("input", function (event) {
    clearTimeout(timer);
    var value = event.target.value;
    timer = setTimeout(function () {
      currentFilter = value.trim().replace(/\s+/g, "").toLowerCase();
      visible = chunkSize;
      render();
    }, 150);
  });
  document.getElementById("poetsMore").addEventListener("click", function () {
    visible += chunkSize;
    render();
  });

  bindFilters();
  render();
})();
