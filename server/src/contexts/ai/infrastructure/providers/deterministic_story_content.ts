import type { TextGenerationTask } from "../../application/ports/text_generation.js";
import { taskWritingLanguage } from "./deterministic_task_language.js";

/**
 * The deterministic provider's fixed chapter-prose tables and builders
 * (DR-023 split for the file-size gate). Every builder is pure and total: the
 * same task always yields the same prose, and the zh variants mirror the en
 * structure — the same cast/pressure/turn slots, the same chapter number and
 * title interpolation — so both languages stay equally deterministic and
 * equally tied to the task's chapter.
 */

const CAST_OPTIONS = [
  ["Mira", "Tomas", "station", "ledger page"],
  ["Ilen", "Rook", "archive stair", "sealed index card"],
  ["Sera", "Vale", "flood market", "brass token"],
  ["Niko", "Adra", "observatory roof", "blackout map"],
] as const;

const PRESSURE_OPTIONS = [
  "a debt that names its collector before the victim",
  "a record filed tomorrow with today's blood still wet",
  "a signal that arrives before the machine is built",
  "a bargain everyone remembers except the person who signed it",
] as const;

const TURN_OPTIONS = [
  "chooses to keep the evidence instead of handing it over",
  "lies once, then has to defend the lie with a true confession",
  "breaks the safest rule in the room to protect a weaker witness",
  "refuses the obvious escape because it would abandon the only proof",
] as const;

const DRAFT_TITLES = [
  "The First Cost",
  "A Record Filed Early",
  "The Witness Under Glass",
  "The Door That Answers Back",
  "Terms Written in Rain",
] as const;

const CHINESE_CAST_OPTIONS = [
  ["米拉", "托马斯", "车站", "账页"],
  ["伊莲", "鲁克", "档案馆的楼梯", "封存的索引卡"],
  ["赛拉", "维尔", "洪水后的集市", "黄铜筹码"],
  ["尼科", "阿德拉", "天文台的屋顶", "停电地图"],
] as const;

const CHINESE_PRESSURE_OPTIONS = [
  "一笔会先报出收债人姓名的债",
  "一份日期署着明天、血迹却还没干透的档案",
  "一个在机器造成之前就抵达的信号",
  "一份所有人都记得、只有签名者自己忘了的契约",
] as const;

const CHINESE_TURN_OPTIONS = [
  "选择留下证据，而不是把它交出去",
  "撒了一次谎，此后只能用真话去圆",
  "为了护住更弱的人，打碎了房间里最安全的规矩",
  "拒绝了最明显的退路，因为那会丢掉唯一的证据",
] as const;

const CHINESE_DRAFT_TITLES = [
  "最初的代价",
  "提前归档的记录",
  "玻璃下的证人",
  "会回话的门",
  "写在雨里的条款",
] as const;

function metadataString(metadata: Record<string, unknown>, key: string, fallback: string): string {
  const value = metadata[key];
  return typeof value === "string" && value.trim() !== "" ? value.trim() : fallback;
}

function metadataNumber(metadata: Record<string, unknown>, key: string): number {
  const value = metadata[key];
  return typeof value === "number" && Number.isFinite(value) && value >= 1 ? Math.floor(value) : 1;
}

function buildEnglishChapterDraft(task: TextGenerationTask): string {
  const chapterNumber = metadataNumber(task.metadata, "chapter_number");
  const title = metadataString(task.metadata, "title", "Untitled Story");
  const genre = metadataString(task.metadata, "genre", "fantasy");
  const premise = metadataString(task.metadata, "premise", "a rumor nobody wanted to own");
  const index = (chapterNumber - 1) % CAST_OPTIONS.length;
  const [protagonist, confidant, setting, objectName] = CAST_OPTIONS[index] ?? CAST_OPTIONS[0];
  const pressure =
    PRESSURE_OPTIONS[(chapterNumber - 1) % PRESSURE_OPTIONS.length] ?? PRESSURE_OPTIONS[0];
  const turn = TURN_OPTIONS[(chapterNumber - 1) % TURN_OPTIONS.length] ?? TURN_OPTIONS[0];
  const chapterTitle = DRAFT_TITLES[(chapterNumber - 1) % DRAFT_TITLES.length] ?? DRAFT_TITLES[0];
  return [
    `# Chapter ${chapterNumber}: ${chapterTitle}`,
    "",
    `The ${setting} had a way of making every private fear sound public. ${protagonist} noticed it in the scrape of shoes, in the hush after doors opened, and in the way the ${genre} city seemed to lean closer whenever someone pretended not to listen.`,
    "",
    `The first pressure in ${title} arrives quietly, before anyone can name it as danger. The trail began with ${premise}, but no trail stayed harmless after midnight. Tonight it had narrowed to ${objectName}, wrapped in plain paper and left where only a frightened friend would think to look.`,
    "",
    `"You should have burned it," ${confidant} said.`,
    "",
    `"You should have warned me before it learned my name," ${protagonist} answered.`,
    "",
    `That made ${confidant} go still. The silence was useful because it showed where the truth pressed hardest. ${protagonist} opened the packet and found one sentence waiting inside it: ${pressure}. The sentence did not behave like a message. It behaved like a door.`,
    "",
    `A vendor shouted two streets away. A lamp failed above them. For a moment the whole district seemed to inhale through the same narrow crack. ${confidant} reached for the packet, but ${protagonist} moved first and ${turn}.`,
    "",
    `That choice changed the room more than the evidence did. People who had looked bored now looked careful. The exit behind ${confidant} filled with someone's shadow, too patient to be an accident.`,
    "",
    `${protagonist} folded the ${objectName} into an inside pocket. "If this is a trap, we spring it where we can see the teeth."`,
    "",
    `The shadow at the exit shifted. ${confidant} did not run. That was the first honest thing either of them had done all night, and it cost them their last quiet minute.`,
  ].join("\n");
}

function buildChineseChapterDraft(task: TextGenerationTask): string {
  const chapterNumber = metadataNumber(task.metadata, "chapter_number");
  const title = metadataString(task.metadata, "title", "未命名故事");
  const genre = metadataString(task.metadata, "genre", "奇幻");
  const premise = metadataString(task.metadata, "premise", "一则没人愿意认领的传闻");
  const index = (chapterNumber - 1) % CHINESE_CAST_OPTIONS.length;
  const [protagonist, confidant, setting, objectName] =
    CHINESE_CAST_OPTIONS[index] ?? CHINESE_CAST_OPTIONS[0];
  const pressure =
    CHINESE_PRESSURE_OPTIONS[(chapterNumber - 1) % CHINESE_PRESSURE_OPTIONS.length] ??
    CHINESE_PRESSURE_OPTIONS[0];
  const turn =
    CHINESE_TURN_OPTIONS[(chapterNumber - 1) % CHINESE_TURN_OPTIONS.length] ??
    CHINESE_TURN_OPTIONS[0];
  const chapterTitle =
    CHINESE_DRAFT_TITLES[(chapterNumber - 1) % CHINESE_DRAFT_TITLES.length] ??
    CHINESE_DRAFT_TITLES[0];
  return [
    `# 第${chapterNumber}章：${chapterTitle}`,
    "",
    `${setting}的夜晚总有一种本事，让私人的恐惧听起来像公开的事情。${protagonist}穿过走廊时，从鞋底的刮擦声、门开之后短暂的安静，以及每个人假装没有侧过头去的姿态里，认出了这种本事。这座${genre}的城市从不缺故事，缺的是愿意为故事负责的人。`,
    "",
    `压力抵达《${title}》的方式很轻，轻到没人肯先承认它是危险。线索从${premise}开始，后来在纸上收窄成一条折痕，最后只剩下${objectName}，用素纸包着，放在一个只有害怕的人才会想到的地方。`,
    "",
    `"你早该把它烧掉，"${confidant}说。`,
    "",
    `"你早该在它记住我的名字之前提醒我，"${protagonist}回答。`,
    "",
    `这句话让${confidant}沉默下来。沉默是有用的，它让人看清真相压得最沉的地方。${protagonist}拆开纸包，里面只有一句话：${pressure}。那句话不像消息，更像一扇门。`,
    "",
    `街口传来小贩的吆喝，头顶的灯忽然灭了一盏。有一瞬间，整条街像是从同一个窄缝里吸气。${confidant}伸手去够纸包，${protagonist}却先一步${turn}。`,
    "",
    `这个选择改变的不是证据，而是房间里的空气。原本无聊的人开始变得小心，出口的方向多出一道影子，耐心得不像偶然。`,
    "",
    `${protagonist}把${objectName}折好，塞进内袋。"如果这是陷阱，我们就在看得见牙齿的地方踩进去。"`,
    "",
    `出口的影子晃了一下。${confidant}没有跑。那是他们整晚第一件诚实的事，也花光了他们最后的安静。`,
  ].join("\n");
}

function buildEnglishChapterRevision(task: TextGenerationTask): string {
  const chapterNumber = metadataNumber(task.metadata, "chapter_number");
  const title = metadataString(task.metadata, "title", "Untitled Story");
  return [
    `# Chapter ${chapterNumber}: The Debt in the Rain`,
    "",
    `Mira waited until the platform emptied before she opened the parcel again. The page still carried the heading ${title}, though the words beneath it had begun to argue with each other. The danger had sounded tidy in Tomas's mouth, as if fear could be catalogued and shelved. It could not. The page trembled whenever she breathed on it, and each tremor pulled another memory loose: her father's sleeve dark with rain, her mother refusing to answer the door, Tomas pretending not to know which name had been crossed out first.`,
    "",
    '"Say it plainly," she told him.',
    "",
    'Tomas looked at the tunnel instead. "Plainly gets people killed."',
    "",
    '"So does ornament."',
    "",
    "That made him face her. Something changed there, not on the page: he stopped performing caution and let the old grief show. When the train arrived, neither of them boarded. They stayed beside the wet rail until the city moved around them, and the ledger page named the next cost in a line too sharp to mistake for metaphor.",
    "",
    "The bell struck again. This time the name it carried was hers, and every lamp along the platform leaned toward the sound.",
  ].join("\n");
}

function buildChineseChapterRevision(task: TextGenerationTask): string {
  const chapterNumber = metadataNumber(task.metadata, "chapter_number");
  const title = metadataString(task.metadata, "title", "未命名故事");
  return [
    `# 第${chapterNumber}章：雨里的债`,
    "",
    `米拉等到站台空了，才重新打开那个纸包。纸页上还留着《${title}》的标题，标题底下的字却开始互相争吵。危险从托马斯嘴里说出来的时候总是整齐的，仿佛恐惧可以编目上架。事实并非如此。她每呼吸一次，纸页就抖一下，抖出一段旧记忆：父亲被雨打湿的袖口，母亲不肯开门的背影，还有托马斯假装不记得是谁的名字先被划掉。`,
    "",
    '"直说。"她对他说。',
    "",
    '托马斯看的是隧道。"直说会死人。"',
    "",
    '"含糊也一样。"',
    "",
    "这句话让他转过头来。变化不在纸上，而在他脸上：他不再表演谨慎，让旧日的悲伤露了出来。列车进站时，两个人都没有上车。他们站在湿漉漉的铁轨旁，任凭城市在周围继续运转，而账页用一行锋利得不像比喻的字，写下了下一笔代价。钟又响了一次。这一次它报出的名字是她，站台两旁的灯全都朝声音的方向倾了过去。",
  ].join("\n");
}

export function buildChapterDraft(task: TextGenerationTask): string {
  return taskWritingLanguage(task) === "zh"
    ? buildChineseChapterDraft(task)
    : buildEnglishChapterDraft(task);
}

export function buildChapterRevision(task: TextGenerationTask): string {
  return taskWritingLanguage(task) === "zh"
    ? buildChineseChapterRevision(task)
    : buildEnglishChapterRevision(task);
}
