import os, sys, re, json, time, random, threading
from zlapi import ZaloAPI
from zlapi.models import Message, ThreadType, Mention, MultiMention
from pyfiglet import figlet_format


class Logger:
	_enabled = True
	_lock = threading.Lock()

	@classmethod
	def on(cls):
		with cls._lock:
			cls._enabled = True

	@classmethod
	def off(cls):
		with cls._lock:
			cls._enabled = False

	@classmethod
	def toggle(cls):
		with cls._lock:
			cls._enabled = not cls._enabled
			return cls._enabled

	@classmethod
	def is_on(cls):
		with cls._lock:
			return cls._enabled

	@classmethod
	def log(cls, msg):
		with cls._lock:
			if cls._enabled:
				print(msg)

	@classmethod
	def force(cls, msg):
		print(msg)


class Timing:
	@staticmethod
	def now():
		return time.time()

	@staticmethod
	def clock(ts=None):
		return time.strftime('%H:%M:%S', time.localtime(ts or time.time()))


class Delay:
	@staticmethod
	def secs(n):
		time.sleep(max(0, n))

	@staticmethod
	def rand(a, b):
		time.sleep(random.uniform(a, b))

	@staticmethod
	def interruptible(duration, interval, stop_event):
		end = time.time() + duration
		while time.time() < end:
			if stop_event.is_set():
				return False
			time.sleep(min(interval, max(0, end - time.time())))
		return True


class ContentParser:
	@staticmethod
	def extract(content):
		if content is None:
			return ''
		if isinstance(content, str):
			try:
				parsed = json.loads(content)
				if isinstance(parsed, dict):
					return str(parsed.get('title', '') or parsed.get('text', '') or parsed.get('content', '') or content)
			except (json.JSONDecodeError, TypeError):
				pass
			return content
		if isinstance(content, dict):
			return str(content.get('title', '') or content.get('text', '') or content.get('content', '') or json.dumps(content, ensure_ascii=False))
		for attr in ('text', 'title', 'content'):
			if hasattr(content, attr):
				return str(getattr(content, attr))
		return str(content)

	@staticmethod
	def preview(content, maxlen=80):
		text = ContentParser.extract(content)
		if not text:
			return '(empty)'
		text = text.replace('\n', ' ').replace('\r', '')
		text = re.sub(r'\s+', ' ', text).strip()
		if not text:
			return '(media/sticker)'
		return text[:maxlen] + '...' if len(text) > maxlen else text


class TextLoader:
	@staticmethod
	def load(filepath):
		if not os.path.exists(filepath):
			Logger.force(f'[ERR] file not found: {filepath}')
			return []
		with open(filepath, 'r', encoding='utf-8') as f:
			lines = [l.strip() for l in f if l.strip()]
		if not lines:
			Logger.force('[ERR] file empty')
		return lines

	@staticmethod
	def create(filepath, samples=None):
		samples = samples or ['hello', 'hi there', 'alo alo', 'ping', 'hey', 'sup', 'yo', 'ok noted']
		with open(filepath, 'w', encoding='utf-8') as f:
			f.writelines(f'{s}\n' for s in samples)
		Logger.force(f'[OK] created [{filepath}]')


class TextPicker:
	def __init__(self, texts, mode='1'):
		self._texts = texts
		self._mode = mode
		self._counter = 0
		self._lock = threading.Lock()

	def pick(self):
		with self._lock:
			if self._mode == '1':
				return random.choice(self._texts)
			text = self._texts[self._counter % len(self._texts)]
			self._counter += 1
			return text


class HumanTyping:
	@staticmethod
	def think():
		r = random.random()
		if r < 0.3:
			return random.uniform(0.3, 1.0)
		elif r < 0.7:
			return random.uniform(1.0, 3.0)
		elif r < 0.9:
			return random.uniform(3.0, 6.0)
		else:
			return random.uniform(6.0, 12.0)

	@staticmethod
	def typing(text):
		n = len(text)
		speed = random.uniform(3.0, 7.0)
		base = n / speed
		if random.random() < 0.15:
			base += random.uniform(0.5, 2.0)
		return max(0.5, min(base, 8.0))

	@staticmethod
	def read_msg(content):
		n = len(ContentParser.extract(content)) if content else 0
		return max(0.3, min(n / random.uniform(15.0, 25.0), 3.0))

	@staticmethod
	def total_reply_delay(text, incoming_content=None):
		read = HumanTyping.read_msg(incoming_content) if incoming_content else 0
		think = HumanTyping.think()
		typing = HumanTyping.typing(text)
		return read + think + typing, read, think, typing

	@staticmethod
	def total_mention_delay(text):
		think = random.uniform(0.5, 2.0)
		typing = HumanTyping.typing(text)
		return think + typing, think, typing

	@staticmethod
	def between_double_msg():
		return random.uniform(0.8, 2.5)

	@staticmethod
	def idle_variation(base_delay):
		variation = base_delay * random.uniform(-0.3, 0.3)
		if random.random() < 0.1:
			variation += random.uniform(5.0, 15.0)
		return max(2.0, base_delay + variation)

	@staticmethod
	def multi_account_offset():
		return random.uniform(2.0, 6.0)


class ReplyMsgObj:
	__slots__ = ('uidFrom', 'msgId', 'cliMsgId', 'msgType', 'content', 'ts')

	def __init__(self, uid_from, msg_id, cli_msg_id, msg_type, content, ts):
		self.uidFrom = uid_from
		self.msgId = msg_id
		self.cliMsgId = cli_msg_id
		self.msgType = msg_type
		self.content = content
		self.ts = ts

	@classmethod
	def from_msg(cls, msg, content_override=None):
		raw = msg.get('content', '')
		return cls(
			uid_from=str(msg.get('uidFrom', '')), msg_id=msg.get('msgId'),
			cli_msg_id=msg.get('cliMsgId'), msg_type=msg.get('msgType', ''),
			content=content_override or ContentParser.extract(raw), ts=msg.get('ts', ''),
		)


class MentionBuilder:
	def __init__(self):
		self._streak = 0

	def reset(self):
		self._streak = 0

	def plain(self, text):
		return Message(text=text)

	def before(self, text, uid, name):
		tag = f'@{name}'
		return Message(text=f'{tag} {text}', mention=MultiMention([Mention(uid=str(uid), offset=0, length=len(tag), auto_format=False)]))

	def after(self, text, uid, name):
		tag = f'@{name}'
		return Message(text=f'{text} {tag}', mention=MultiMention([Mention(uid=str(uid), offset=len(text) + 1, length=len(tag), auto_format=False)]))

	def multi_after(self, text, users):
		mentions, suffix, offset = [], '', len(text) + 1
		for u in users:
			tag = f'@{u["name"]}'
			mentions.append(Mention(uid=str(u['id']), offset=offset, length=len(tag), auto_format=False))
			suffix += f'{tag} '
			offset += len(tag) + 1
		return Message(text=f'{text} {suffix.strip()}', mention=MultiMention(mentions))

	def random_mention(self, text, target_map):
		users = [{'id': uid, 'name': name} for uid, name in target_map.items()]
		if len(users) == 1:
			u = users[0]
			return random.choice([self.before, self.after])(text, u['id'], u['name'])
		self._streak += 1
		if self._streak <= random.randint(5, 8):
			selected = random.sample(users, random.randint(2, len(users)))
			return self.multi_after(text, selected)
		self._streak = 0
		u = random.choice(users)
		return random.choice([self.before, self.after])(text, u['id'], u['name'])

	def random_style(self, text, target_map):
		return self.random_mention(text, target_map), 'mention'


class TargetStore:
	STORE_FILE = 'targets_store.json'

	@classmethod
	def _load_all(cls):
		if not os.path.exists(cls.STORE_FILE):
			return {}
		try:
			with open(cls.STORE_FILE, 'r', encoding='utf-8') as f:
				return json.load(f)
		except:
			return {}

	@classmethod
	def _save_all(cls, data):
		with open(cls.STORE_FILE, 'w', encoding='utf-8') as f:
			json.dump(data, f, ensure_ascii=False, indent=2)

	@classmethod
	def save(cls, key, targets):
		data = cls._load_all()
		data[str(key)] = targets
		cls._save_all(data)

	@classmethod
	def load(cls, key):
		return cls._load_all().get(str(key), {})

	@classmethod
	def has(cls, key):
		return str(key) in cls._load_all()

	@classmethod
	def merge(cls, key, new_targets):
		existing = cls.load(key)
		existing.update(new_targets)
		cls.save(key, existing)
		return existing


class AccountStore:
	STORE_FILE = 'accounts_store.json'

	@classmethod
	def _load_all(cls):
		if not os.path.exists(cls.STORE_FILE):
			return []
		try:
			with open(cls.STORE_FILE, 'r', encoding='utf-8') as f:
				return json.load(f)
		except:
			return []

	@classmethod
	def _save_all(cls, data):
		with open(cls.STORE_FILE, 'w', encoding='utf-8') as f:
			json.dump(data, f, ensure_ascii=False, indent=2)

	@classmethod
	def add(cls, name, imei, cookies):
		accs = cls._load_all()
		accs.append({'name': name, 'imei': imei, 'cookies': cookies})
		cls._save_all(accs)

	@classmethod
	def list_all(cls):
		return cls._load_all()


class Bot(ZaloAPI):
	def __init__(self, imei, cookies, label='bot'):
		super().__init__('api_key', 'secret_key', imei, cookies)
		self._last_reconnect = Timing.now()
		self._stats = {'send': 0, 'fail': 0, 'cfail': 0}
		self.mention = MentionBuilder()
		self.label = label

	def _should_reconnect(self):
		return Timing.now() - self._last_reconnect > 7200

	def reconnect(self):
		self._last_reconnect = Timing.now()
		Logger.log(f'[{self.label}] reconnecting...')
		Delay.secs(2)

	def _retry(self, fn, label='send'):
		for attempt in range(10):
			try:
				if self._should_reconnect():
					self.reconnect()
				fn()
				self._stats['send'] += 1
				self._stats['cfail'] = 0
				return True
			except Exception as e:
				self._stats['fail'] += 1
				self._stats['cfail'] += 1
				err = str(e).lower()
				Logger.log(f'[{self.label}][ERR] {label} attempt {attempt + 1}: {e}')
				if any(k in err for k in ('session', 'token', 'login', 'auth', 'expired')):
					self.reconnect()
					Delay.secs(5)
				elif any(k in err for k in ('rate', 'limit', 'spam', 'block', 'banned')):
					Delay.secs(60 * (attempt + 1))
				else:
					Delay.secs(2 ** min(attempt, 5))
				if self._stats['cfail'] >= 3:
					self.reconnect()
					Delay.secs(10)
					self._stats['cfail'] = 0
		self.reconnect()
		return False

	def safe_send(self, msg, tid, ttype):
		return self._retry(lambda: self.send(msg, tid, ttype), 'send')

	def safe_reply(self, msg_obj, reply_obj, tid, ttype):
		return self._retry(lambda: self.replyMessage(msg_obj, reply_obj, tid, ttype), 'reply')

	def join_and_get_group(self, group_link):
		try:
			group_data = self.getIDsGroup(group_link)
		except Exception as e:
			Logger.force(f'[{self.label}][ERR] get group: {e}')
			return None
		if not group_data or not isinstance(group_data, dict):
			return None
		gid = group_data.get('groupId')
		gname = group_data.get('name', 'Unknown')
		if not gid:
			return None
		try:
			self.joinGroup(group_link)
		except:
			pass
		members = []
		for mem in group_data.get('currentMems', []):
			mid = mem.get('id', '')
			mname = mem.get('dName') or mem.get('zaloName') or f'User_{mid}'
			if mid:
				members.append({'id': str(mid), 'name': mname})
		return {'id': str(gid), 'name': gname, 'members': members, 'totalMember': group_data.get('totalMember', len(members))}

	def get_groups(self):
		try:
			result = []
			for gid in self.fetchAllGroups().gridVerMap:
				info = self.fetchGroupInfo(gid)
				result.append({'id': gid, 'name': info.gridInfoMap[gid]['name']})
			return result
		except Exception as e:
			Logger.force(f'[ERR] fetch groups: {e}')
			return []

	def get_members(self, gid):
		try:
			info = self.fetchGroupInfo(gid)
			members = []
			for mem in info.gridInfoMap[gid]['memVerList']:
				uid = mem.split('_')[0]
				try:
					uinfo = self.fetchUserInfo(uid)
					name = uinfo.changed_profiles[uid]['displayName']
				except:
					name = f'User_{uid}'
				members.append({'id': uid, 'name': name})
			return members
		except Exception as e:
			Logger.force(f'[ERR] fetch members: {e}')
			return []

	def get_latest_target_msg(self, gid, target_uids, after_id):
		try:
			data = self.getRecentGroup(gid)
			msgs = data.get('groupMsgs', [])
			latest = None
			for m in msgs:
				mid = m.get('msgId')
				if mid and str(m.get('uidFrom', '')) in target_uids and int(mid) > after_id:
					latest = m
			return latest, msgs
		except:
			return None, []

	def get_last_seen(self, gid):
		try:
			data = self.getRecentGroup(gid)
			msgs = data.get('groupMsgs', [])
			return int(msgs[-1].get('msgId')) if msgs else 0
		except:
			return 0


class ResponseDecider:
	def __init__(self):
		self._consecutive_replies = 0

	def decide(self):
		r = random.random()
		if self._consecutive_replies >= 3:
			if r < 0.25: action = 'reply'
			elif r < 0.45: action = 'mention_only'
			elif r < 0.65: action = 'plain'
			elif r < 0.80: action = 'double'
			else: action = 'skip_then_reply'
		else:
			if r < 0.35: action = 'reply'
			elif r < 0.55: action = 'mention_only'
			elif r < 0.70: action = 'plain'
			elif r < 0.85: action = 'double'
			else: action = 'skip_then_reply'
		if action in ('reply', 'skip_then_reply'):
			self._consecutive_replies += 1
		else:
			self._consecutive_replies = 0
		return action


class Prompt:
	@staticmethod
	def clear():
		os.system('cls' if os.name == 'nt' else 'clear')

	@staticmethod
	def banner():
		Prompt.clear()
		print(figlet_format('AutoReply', font='slant'))
		print('Auto Reply & Mention Tool for Zalo'.center(60))
		print('=' * 60)

	@staticmethod
	def cookies(raw):
		try:
			return json.loads(raw.strip())
		except json.JSONDecodeError:
			Logger.force('[ERR] invalid cookie json')
			return None

	@staticmethod
	def select_group_by_link(bot):
		link = input('\n> group link: ').strip()
		if not link:
			return None, None, []
		result = bot.join_and_get_group(link)
		if not result:
			return None, None, []
		Logger.force(f'\n[OK] group: {result["name"]} | id: {result["id"]} | members: {result["totalMember"]}')
		return result['id'], result['name'], result['members']

	@staticmethod
	def select_group(bot):
		groups = bot.get_groups()
		if not groups:
			Logger.force('[WARN] no groups')
			return None, None
		Logger.force('\n[GROUPS]')
		for i, g in enumerate(groups, 1):
			Logger.force(f'  {i}. {g["name"]} | {g["id"]}')
		try:
			idx = int(input('\n> select: ')) - 1
			if 0 <= idx < len(groups):
				return groups[idx]['id'], groups[idx]['name']
		except:
			pass
		return None, None

	@staticmethod
	def select_members_from_list(members, gname, exclude_uids=None):
		if not members:
			return {}
		exclude_uids = exclude_uids or set()
		available = [m for m in members if m['id'] not in exclude_uids]
		if not available:
			Logger.force('[WARN] no new members to add')
			return {}
		Logger.force(f'\n[MEMBERS] {gname}')
		for i, m in enumerate(available, 1):
			Logger.force(f'  {i}. {m["name"]} | {m["id"]}')
		raw = input('\n> select (comma sep): ').strip()
		try:
			indices = [int(x.strip()) - 1 for x in raw.split(',') if x.strip().isdigit()]
		except:
			return {}
		targets = {}
		for i in indices:
			if 0 <= i < len(available):
				targets[available[i]['id']] = available[i]['name']
		return targets

	@staticmethod
	def select_members(bot, gid, gname, exclude_uids=None):
		return Prompt.select_members_from_list(bot.get_members(gid), gname, exclude_uids)

	@staticmethod
	def select_file():
		path = input('\n> text file (default hello.txt): ').strip() or 'hello.txt'
		texts = TextLoader.load(path)
		if not texts:
			return None, None
		Logger.force(f'[OK] {len(texts)} lines from [{path}]')
		for i, t in enumerate(texts[:5], 1):
			Logger.force(f'  {i}. {t[:50]}')
		if len(texts) > 5:
			Logger.force(f'  ... +{len(texts) - 5} more')
		return texts, path

	@staticmethod
	def select_mode():
		Logger.force('\n[MODE] 1.random 2.sequential')
		m = input('> (1/2, default 1): ').strip()
		return m if m in ('1', '2') else '1'

	@staticmethod
	def input_int(prompt, default):
		raw = input(prompt).strip()
		try:
			return int(raw) if raw else default
		except:
			return default

	@staticmethod
	def input_float(prompt, default):
		raw = input(prompt).strip()
		try:
			return float(raw) if raw else default
		except:
			return default

	@staticmethod
	def ask_use_saved_targets(key, members=None):
		if not TargetStore.has(key):
			return None
		saved = TargetStore.load(key)
		Logger.force(f'\n[SAVED] {len(saved)} target(s):')
		for uid, name in saved.items():
			Logger.force(f'  - {name} ({uid})')
		ch = input('> use saved targets? (y/n, default y): ').strip().lower()
		if ch == 'n':
			return None
		add_ch = input('> add more targets to saved? (y/n, default n): ').strip().lower()
		if add_ch == 'y' and members:
			new_targets = Prompt.select_members_from_list(members, 'add targets', exclude_uids=set(saved.keys()))
			if new_targets:
				saved.update(new_targets)
				TargetStore.save(key, saved)
				Logger.force(f'[OK] updated to {len(saved)} target(s):')
				for uid, name in saved.items():
					Logger.force(f'  - {name} ({uid})')
		return saved


class BotContext:
	def __init__(self, bot, gid, targets):
		self.bot = bot
		self.gid = gid
		self.targets = targets
		self.target_uids = set(targets.keys())


class Engine:
	def __init__(self, bot):
		self._bot = bot
		self._decider = ResponseDecider()

	def _update_seen(self, msgs, seen_id):
		for m in msgs:
			mid = m.get('msgId')
			if mid and int(mid) > seen_id:
				seen_id = int(mid)
		return seen_id

	def _check_new(self, gid, target_uids, seen_id):
		latest, all_msgs = self._bot.get_latest_target_msg(gid, target_uids, seen_id)
		return latest, all_msgs, self._update_seen(all_msgs, seen_id)

	def _interruptible_wait(self, duration, gid, target_uids, seen_id, stop):
		end = Timing.now() + duration
		while Timing.now() < end:
			if stop.is_set():
				return None, seen_id
			Delay.secs(min(0.3, max(0, end - Timing.now())))
			latest, all_msgs, new_seen = self._check_new(gid, target_uids, seen_id)
			seen_id = new_seen
			if latest:
				return latest, seen_id
		return None, seen_id

	def _do_reply(self, msg, text, uid, name, gid, stats):
		reply_obj = ReplyMsgObj.from_msg(msg)
		msg_obj = self._bot.mention.before(text, uid, name)
		if self._bot.safe_reply(msg_obj, reply_obj, gid, ThreadType.GROUP):
			stats['reply'] += 1
			Logger.log(f'  [{self._bot.label}][REPLY] #{stats["reply"]}: @{name} {text[:50]}')
			return True
		return False

	def _do_mention(self, text, targets, gid, stats):
		msg_obj = self._bot.mention.random_mention(text, targets)
		if self._bot.safe_send(msg_obj, gid, ThreadType.GROUP):
			stats['mention'] += 1
			Logger.log(f'  [{self._bot.label}][TAG] #{stats["mention"]}: {text[:50]}')
			return True
		return False

	def _do_plain(self, text, gid, stats):
		msg_obj = self._bot.mention.plain(text)
		if self._bot.safe_send(msg_obj, gid, ThreadType.GROUP):
			stats['plain'] += 1
			Logger.log(f'  [{self._bot.label}][PLAIN] #{stats["plain"]}: {text[:50]}')
			return True
		return False

	def _handle_target_msg(self, msg, picker, targets, gid, seen_id, stats, stop):
		uid = str(msg.get('uidFrom', ''))
		name = targets.get(uid, 'Unknown')
		Logger.log(f'\n[{self._bot.label}][MSG] [{name}]: {ContentParser.preview(msg.get("content", ""))}')
		action = self._decider.decide()
		text1 = picker.pick()
		total, r, th, ty = HumanTyping.total_reply_delay(text1, msg.get('content', ''))
		if action == 'skip_then_reply':
			total += random.uniform(5.0, 20.0)
			action = 'reply'
		Logger.log(f'  [{self._bot.label}][HUMAN] {total:.1f}s [{action}]')
		newer, seen_id = self._interruptible_wait(total, gid, set(targets.keys()), seen_id, stop)
		if newer:
			uid = str(newer.get('uidFrom', ''))
			name = targets.get(uid, 'Unknown')
			msg = newer
			Delay.secs(HumanTyping.typing(text1) * 0.3)
		if action == 'reply':
			self._do_reply(msg, text1, uid, name, gid, stats)
		elif action == 'mention_only':
			self._do_mention(text1, targets, gid, stats)
		elif action == 'plain':
			self._do_plain(text1, gid, stats)
		elif action == 'double':
			fs = random.choice(['reply', 'mention_only', 'plain'])
			if fs == 'reply': self._do_reply(msg, text1, uid, name, gid, stats)
			elif fs == 'mention_only': self._do_mention(text1, targets, gid, stats)
			else: self._do_plain(text1, gid, stats)
			text2 = picker.pick()
			gap = HumanTyping.between_double_msg() + HumanTyping.typing(text2)
			Logger.log(f'  [{self._bot.label}][DOUBLE] gap:{gap:.1f}s')
			Delay.secs(gap)
			if random.choice([True, False]):
				self._do_mention(text2, targets, gid, stats)
			else:
				self._do_plain(text2, gid, stats)
		seen_id = max(seen_id, int(msg.get('msgId', 0)))
		Delay.rand(0.3, 1.0)
		return seen_id

	def run_combined(self, gid, targets, picker, delay_check, delay_mention, msg_limit, stats, stop):
		seen_id = self._bot.get_last_seen(gid)
		sent = 0
		target_uids = set(targets.keys())
		while not stop.is_set():
			try:
				latest, all_msgs, new_seen = self._check_new(gid, target_uids, seen_id)
				seen_id = new_seen
				if latest:
					seen_id = self._handle_target_msg(latest, picker, targets, gid, seen_id, stats, stop)
					Delay.rand(0.2, 0.5)
					continue
				if sent >= msg_limit:
					rest = random.randint(25, 40)
					Logger.log(f'\n[{self._bot.label}][REST] {msg_limit} sent -> {rest}min')
					rest_end = Timing.now() + rest * 60
					while Timing.now() < rest_end:
						if stop.is_set(): return
						latest, _, new_seen = self._check_new(gid, target_uids, seen_id)
						seen_id = new_seen
						if latest:
							seen_id = self._handle_target_msg(latest, picker, targets, gid, seen_id, stats, stop)
						Delay.secs(delay_check)
					sent = 0
					self._bot.mention.reset()
					self._decider = ResponseDecider()
					continue
				text = picker.pick()
				mt, _, _ = HumanTyping.total_mention_delay(text)
				idle = HumanTyping.idle_variation(delay_mention)
				newer, seen_id = self._interruptible_wait(idle + mt, gid, target_uids, seen_id, stop)
				if newer:
					seen_id = self._handle_target_msg(newer, picker, targets, gid, seen_id, stats, stop)
					continue
				msg_obj, style = self._bot.mention.random_style(text, targets)
				if self._bot.safe_send(msg_obj, gid, ThreadType.GROUP):
					sent += 1
					stats['mention'] += 1
					Logger.log(f'[{self._bot.label}][SEND] #{stats["mention"]} [{sent}/{msg_limit}] ({style}): {text[:50]}')
				Delay.rand(0.3, 0.8)
			except KeyboardInterrupt:
				break
			except Exception as e:
				Logger.log(f'[{self._bot.label}][ERR] {e}')
				Delay.secs(1)

	def run_combined_nonstop(self, gid, targets, picker, delay_check, delay_mention, stats, stop):
		seen_id = self._bot.get_last_seen(gid)
		target_uids = set(targets.keys())
		while not stop.is_set():
			try:
				latest, all_msgs, new_seen = self._check_new(gid, target_uids, seen_id)
				seen_id = new_seen
				if latest:
					seen_id = self._handle_target_msg(latest, picker, targets, gid, seen_id, stats, stop)
					Delay.rand(0.2, 0.5)
					continue
				text = picker.pick()
				mt, _, _ = HumanTyping.total_mention_delay(text)
				idle = HumanTyping.idle_variation(delay_mention)
				newer, seen_id = self._interruptible_wait(idle + mt, gid, target_uids, seen_id, stop)
				if newer:
					seen_id = self._handle_target_msg(newer, picker, targets, gid, seen_id, stats, stop)
					continue
				msg_obj, style = self._bot.mention.random_style(text, targets)
				if self._bot.safe_send(msg_obj, gid, ThreadType.GROUP):
					stats['mention'] += 1
					Logger.log(f'[{self._bot.label}][SEND] #{stats["mention"]} ({style}): {text[:50]}')
				Delay.rand(0.3, 0.8)
			except KeyboardInterrupt:
				break
			except Exception as e:
				Logger.log(f'[{self._bot.label}][ERR] {e}')
				Delay.secs(1)

	def run_reply_only(self, gid, targets, picker, delay_check, stats, stop):
		seen_id = self._bot.get_last_seen(gid)
		target_uids = set(targets.keys())
		while not stop.is_set():
			try:
				latest, all_msgs, new_seen = self._check_new(gid, target_uids, seen_id)
				seen_id = new_seen
				if not latest:
					Delay.secs(delay_check)
					continue
				seen_id = self._handle_target_msg(latest, picker, targets, gid, seen_id, stats, stop)
			except KeyboardInterrupt:
				break
			except Exception as e:
				Logger.log(f'[{self._bot.label}][ERR] {e}')
				Delay.secs(1)

	def run_mention_only(self, gid, targets, picker, delay_mention, msg_limit, stats, stop):
		sent = 0
		while not stop.is_set():
			try:
				text = picker.pick()
				total, _, _ = HumanTyping.total_mention_delay(text)
				idle = HumanTyping.idle_variation(delay_mention)
				if not Delay.interruptible(idle + total, 0.3, stop):
					return
				msg_obj, style = self._bot.mention.random_style(text, targets)
				if self._bot.safe_send(msg_obj, gid, ThreadType.GROUP):
					sent += 1
					stats['mention'] += 1
					Logger.log(f'[{self._bot.label}][SEND] #{stats["mention"]} [{sent}/{msg_limit}] ({style}): {text[:50]}')
				if sent >= msg_limit:
					rest = random.randint(25, 40)
					Logger.log(f'\n[{self._bot.label}][REST] {msg_limit} sent -> {rest}min')
					if not Delay.interruptible(rest * 60, 1, stop):
						return
					sent = 0
					self._bot.mention.reset()
				Delay.rand(0.3, 0.8)
			except KeyboardInterrupt:
				break
			except Exception as e:
				Logger.log(f'[{self._bot.label}][ERR] {e}')
				Delay.secs(1)

	def run_continuous_mention(self, gid, targets, picker, delay_mention, stats, stop):
		while not stop.is_set():
			try:
				text = picker.pick()
				total, _, _ = HumanTyping.total_mention_delay(text)
				idle = HumanTyping.idle_variation(delay_mention)
				if not Delay.interruptible(idle + total, 0.3, stop):
					return
				msg_obj, style = self._bot.mention.random_style(text, targets)
				if self._bot.safe_send(msg_obj, gid, ThreadType.GROUP):
					stats['mention'] += 1
					Logger.log(f'[{self._bot.label}][SEND] #{stats["mention"]} ({style}): {text[:50]}')
				Delay.rand(0.3, 0.8)
			except KeyboardInterrupt:
				break
			except Exception as e:
				Logger.log(f'[{self._bot.label}][ERR] {e}')
				Delay.secs(1)


class MultiAccountEngine:
	def __init__(self, bot_contexts):
		self._contexts = bot_contexts
		self._send_lock = threading.Lock()
		self._last_send_time = 0.0
		self._min_gap = 2.0

	def _wait_send_gap(self, bot_label):
		with self._send_lock:
			now = Timing.now()
			elapsed = now - self._last_send_time
			if elapsed < self._min_gap:
				wait = self._min_gap - elapsed + random.uniform(0.5, 2.0)
				Logger.log(f'  [{bot_label}][GAP] {wait:.1f}s')
				Delay.secs(wait)
			self._last_send_time = Timing.now()

	def _safe_send_with_gap(self, bot, msg_obj, gid, bot_label):
		self._wait_send_gap(bot_label)
		return bot.safe_send(msg_obj, gid, ThreadType.GROUP)

	def _safe_reply_with_gap(self, bot, msg_obj, reply_obj, gid, bot_label):
		self._wait_send_gap(bot_label)
		return bot.safe_reply(msg_obj, reply_obj, gid, ThreadType.GROUP)

	def run_multi_combined(self, picker, delay_check, delay_mention, msg_limit, stats, stop):
		seen_data = {}
		seen_lock = threading.Lock()
		bot_stats = [{'reply': 0, 'mention': 0, 'plain': 0} for _ in self._contexts]
		deciders = [ResponseDecider() for _ in self._contexts]
		bot_sent = [0 for _ in self._contexts]
		handling_lock = threading.Lock()
		handling_msg_id = [None]

		for i, ctx in enumerate(self._contexts):
			seen_data[i] = ctx.bot.get_last_seen(ctx.gid)

		def update_stats():
			stats['reply'] = sum(s['reply'] for s in bot_stats)
			stats['mention'] = sum(s['mention'] for s in bot_stats)
			stats['plain'] = sum(s['plain'] for s in bot_stats)

		def check_new(idx):
			ctx = self._contexts[idx]
			with seen_lock:
				current = seen_data[idx]
			latest, all_msgs = ctx.bot.get_latest_target_msg(ctx.gid, ctx.target_uids, current)
			new_seen = current
			for m in all_msgs:
				mid = m.get('msgId')
				if mid and int(mid) > new_seen:
					new_seen = int(mid)
			with seen_lock:
				seen_data[idx] = max(seen_data[idx], new_seen)
			return latest

		def do_send_action(ctx, bot_idx, style, text, msg=None, uid=None, name=None):
			bot = ctx.bot
			if style == 'reply' and msg and uid and name:
				reply_obj = ReplyMsgObj.from_msg(msg)
				msg_obj = bot.mention.before(text, uid, name)
				if self._safe_reply_with_gap(bot, msg_obj, reply_obj, ctx.gid, bot.label):
					bot_stats[bot_idx]['reply'] += 1
					Logger.log(f'  [{bot.label}][REPLY] @{name} {text[:40]}')
					update_stats()
					return True
			elif style == 'mention_only':
				msg_obj = bot.mention.random_mention(text, ctx.targets)
				if self._safe_send_with_gap(bot, msg_obj, ctx.gid, bot.label):
					bot_stats[bot_idx]['mention'] += 1
					Logger.log(f'  [{bot.label}][TAG] {text[:40]}')
					update_stats()
					return True
			else:
				msg_obj = bot.mention.plain(text)
				if self._safe_send_with_gap(bot, msg_obj, ctx.gid, bot.label):
					bot_stats[bot_idx]['plain'] += 1
					Logger.log(f'  [{bot.label}][PLAIN] {text[:40]}')
					update_stats()
					return True
			return False

		def handle_msg_for_bot(msg, bot_idx):
			ctx = self._contexts[bot_idx]
			uid = str(msg.get('uidFrom', ''))
			name = ctx.targets.get(uid, 'Unknown')
			text1 = picker.pick()
			action = deciders[bot_idx].decide()
			if action == 'skip_then_reply':
				Delay.secs(random.uniform(5.0, 20.0))
				action = 'reply'
			total, _, _, _ = HumanTyping.total_reply_delay(text1, msg.get('content', ''))
			Logger.log(f'  [{ctx.bot.label}][HUMAN] {total:.1f}s [{action}]')
			Delay.secs(total)
			if action == 'double':
				fs = random.choice(['reply', 'mention_only', 'plain'])
				do_send_action(ctx, bot_idx, fs, text1, msg, uid, name)
				text2 = picker.pick()
				gap = HumanTyping.between_double_msg() + HumanTyping.typing(text2)
				Logger.log(f'  [{ctx.bot.label}][DOUBLE] gap:{gap:.1f}s')
				Delay.secs(gap)
				ss = random.choice(['mention_only', 'plain'])
				do_send_action(ctx, bot_idx, ss, text2, msg, uid, name)
			else:
				do_send_action(ctx, bot_idx, action, text1, msg, uid, name)
			with seen_lock:
				seen_data[bot_idx] = max(seen_data[bot_idx], int(msg.get('msgId', 0)))

		def handle_msg_multi(msg, trigger_idx):
			msg_id = msg.get('msgId')
			with handling_lock:
				if handling_msg_id[0] == msg_id:
					return
				handling_msg_id[0] = msg_id
			uid = str(msg.get('uidFrom', ''))
			trigger_ctx = self._contexts[trigger_idx]
			name = trigger_ctx.targets.get(uid, 'Unknown')
			Logger.log(f'\n[MULTI][MSG] [{name}]: {ContentParser.preview(msg.get("content", ""))}')
			do_sync = random.random() < 0.2 and len(self._contexts) > 1
			if do_sync:
				Logger.log(f'  [MULTI][SYNC] both responding')
				primary_idx = trigger_idx
				secondary_idx = random.choice([i for i in range(len(self._contexts)) if i != primary_idx])
				handle_msg_for_bot(msg, primary_idx)
				sync_gap = random.uniform(3.0, 8.0)
				Logger.log(f'  [MULTI][SYNC] gap: {sync_gap:.1f}s')
				Delay.secs(sync_gap)
				s_ctx = self._contexts[secondary_idx]
				s_latest = check_new(secondary_idx)
				text2 = picker.pick()
				typing_delay = HumanTyping.typing(text2)
				Delay.secs(typing_delay)
				action2 = random.choice(['reply', 'mention_only', 'plain'])
				s_uid = uid
				s_name = s_ctx.targets.get(uid, 'Unknown')
				for s_target_uid, s_target_name in s_ctx.targets.items():
					if s_target_name == name:
						s_uid = s_target_uid
						s_name = s_target_name
						break
				do_send_action(s_ctx, secondary_idx, action2, text2, s_latest or msg, s_uid, s_name)
				with seen_lock:
					seen_data[secondary_idx] = max(seen_data[secondary_idx], int(msg.get('msgId', 0)))
			else:
				handle_msg_for_bot(msg, trigger_idx)

		def bot_worker(idx):
			ctx = self._contexts[idx]
			bot = ctx.bot
			Delay.secs(idx * random.uniform(2.0, 5.0))
			while not stop.is_set():
				try:
					latest = check_new(idx)
					if latest:
						handle_msg_multi(latest, idx)
						Delay.rand(1.0, 3.0)
						continue
					if bot_sent[idx] >= msg_limit:
						rest = random.randint(25, 40)
						Logger.log(f'\n[{bot.label}][REST] {msg_limit} sent -> {rest}min')
						rest_end = Timing.now() + rest * 60
						while Timing.now() < rest_end:
							if stop.is_set(): return
							lt = check_new(idx)
							if lt: handle_msg_multi(lt, idx)
							Delay.secs(delay_check)
						bot_sent[idx] = 0
						bot.mention.reset()
						continue
					base_delay = delay_mention * (1.0 + idx * 0.5)
					text = picker.pick()
					mt, _, _ = HumanTyping.total_mention_delay(text)
					idle = HumanTyping.idle_variation(base_delay)
					wait_end = Timing.now() + idle + mt
					interrupted = False
					while Timing.now() < wait_end:
						if stop.is_set(): return
						Delay.secs(min(0.5, max(0, wait_end - Timing.now())))
						lt = check_new(idx)
						if lt:
							handle_msg_multi(lt, idx)
							interrupted = True
							break
					if interrupted:
						continue
					msg_obj, style = bot.mention.random_style(text, ctx.targets)
					if self._safe_send_with_gap(bot, msg_obj, ctx.gid, bot.label):
						bot_sent[idx] += 1
						bot_stats[idx]['mention'] += 1
						update_stats()
						Logger.log(f'[{bot.label}][SEND] #{bot_stats[idx]["mention"]} [{bot_sent[idx]}/{msg_limit}] ({style}): {text[:50]}')
					Delay.rand(1.0, 3.0)
				except Exception as e:
					Logger.log(f'[{bot.label}][ERR] {e}')
					Delay.secs(2)

		threads = []
		for i in range(len(self._contexts)):
			t = threading.Thread(target=bot_worker, args=(i,), daemon=True)
			t.start()
			threads.append(t)
		while not stop.is_set():
			try:
				Delay.secs(1)
			except KeyboardInterrupt:
				break
		for t in threads:
			t.join(timeout=5)


class TabManager:
	def __init__(self):
		self._tabs = {}
		self._lock = threading.Lock()
		self._next_id = 1

	def add_tab(self, name, target_fn, args, stats, stat_keys):
		stop = threading.Event()
		t = threading.Thread(target=target_fn, args=(*args, stats, stop), daemon=True)
		with self._lock:
			tab_id = self._next_id
			self._next_id += 1
			self._tabs[tab_id] = {
				'name': name, 'thread': t, 'stop': stop,
				'stats': stats, 'stat_keys': stat_keys,
				'started': Timing.clock(), 'running': True,
			}
		t.start()
		Logger.force(f'[TAB] started: {name} (id: {tab_id})')
		return tab_id

	def stop_tab(self, tab_id):
		with self._lock:
			tab = self._tabs.get(tab_id)
			if not tab:
				Logger.force(f'[ERR] tab {tab_id} not found')
				return
			tab['stop'].set()
			tab['running'] = False
			Logger.force(f'[TAB] stopped: {tab["name"]} (id: {tab_id})')

	def stop_all(self):
		with self._lock:
			for t in self._tabs.values():
				if t['running']:
					t['stop'].set()
					t['running'] = False
		Logger.force('[TAB] all stopped')

	def list_tabs(self):
		with self._lock:
			if not self._tabs:
				Logger.force('[TAB] no tabs')
				return
			Logger.force(f'\n{"=" * 70}')
			Logger.force(f'{"ID":<5} {"Name":<30} {"Status":<10} {"Started":<10} {"Stats"}')
			Logger.force(f'{"=" * 70}')
			for tid, tab in self._tabs.items():
				alive = tab['thread'].is_alive()
				if not alive: tab['running'] = False
				status = 'RUNNING' if tab['running'] and alive else 'STOPPED'
				ss = ' | '.join(f'{k}:{tab["stats"].get(k,0)}' for k in tab['stat_keys'])
				Logger.force(f'{tid:<5} {tab["name"]:<30} {status:<10} {tab["started"]:<10} {ss}')
			Logger.force(f'{"=" * 70}')

	def remove_stopped(self):
		with self._lock:
			rm = [t for t, v in self._tabs.items() if not v['running'] and not v['thread'].is_alive()]
			for t in rm: del self._tabs[t]
		Logger.force(f'[TAB] removed {len(rm)}' if rm else '[TAB] nothing to remove')

	def show_menu(self):
		while True:
			Logger.force(f'\n{"=" * 40}')
			Logger.force('       ===== TAB MANAGER =====')
			Logger.force(f'  l.list  s.stop  a.stop all  c.clean  o.log({("ON" if Logger.is_on() else "OFF")})  b.back')
			Logger.force(f'{"=" * 40}')
			ch = input('> ').strip().lower()
			if ch == 'l': self.list_tabs()
			elif ch == 's':
				self.list_tabs()
				try: self.stop_tab(int(input('> id: ').strip()))
				except: Logger.force('[ERR]')
			elif ch == 'a': self.stop_all()
			elif ch == 'c': self.remove_stopped()
			elif ch == 'o': Logger.force(f'[LOG] {"ON" if Logger.toggle() else "OFF"}')
			elif ch == 'b': break


class App:
	def __init__(self):
		self._bots = []
		self._engines = []
		self._tab_mgr = TabManager()

	def _add_account(self):
		name = input('> account name: ').strip() or f'acc_{len(self._bots)+1}'
		imei = input('> IMEI: ').strip()
		cookies = Prompt.cookies(input('> Cookie JSON: ').strip())
		if not cookies: return None
		bot = Bot(imei, cookies, label=name)
		self._bots.append(bot)
		self._engines.append(Engine(bot))
		AccountStore.add(name, imei, cookies)
		Logger.force(f'[OK] [{name}] added (total: {len(self._bots)})')
		return bot

	def _load_saved_accounts(self):
		saved = AccountStore.list_all()
		if not saved: return
		Logger.force(f'\n[SAVED] {len(saved)} account(s):')
		for i, a in enumerate(saved, 1):
			Logger.force(f'  {i}. {a["name"]}')
		if input('> load? (y/n, default y): ').strip().lower() == 'n': return
		for a in saved:
			try:
				bot = Bot(a['imei'], a['cookies'], label=a['name'])
				self._bots.append(bot)
				self._engines.append(Engine(bot))
				Logger.force(f'  [OK] {a["name"]}')
			except Exception as e:
				Logger.force(f'  [ERR] {a["name"]}: {e}')

	def init(self):
		Prompt.banner()
		self._load_saved_accounts()
		if not self._bots:
			Logger.force('\n[SETUP] add account')
			if not self._add_account(): sys.exit(1)

	def _select_bot(self):
		if len(self._bots) == 1:
			return self._bots[0], self._engines[0]
		Logger.force('\n[ACCOUNTS]')
		for i, b in enumerate(self._bots, 1):
			Logger.force(f'  {i}. {b.label}')
		try:
			idx = int(input('> select: ').strip()) - 1
			if 0 <= idx < len(self._bots):
				return self._bots[idx], self._engines[idx]
		except: pass
		return self._bots[0], self._engines[0]

	def _select_multi_bots(self):
		if len(self._bots) < 2:
			Logger.force('[WARN] need 2+ accounts')
			return None
		Logger.force('\n[ACCOUNTS]')
		for i, b in enumerate(self._bots, 1):
			Logger.force(f'  {i}. {b.label}')
		raw = input('> select (comma sep): ').strip()
		try:
			indices = [int(x.strip()) - 1 for x in raw.split(',') if x.strip().isdigit()]
		except: return None
		selected = [self._bots[i] for i in indices if 0 <= i < len(self._bots)]
		if len(selected) < 2:
			Logger.force('[ERR] need 2+')
			return None
		return selected

	def _get_group_and_targets(self, bot):
		Logger.force('\n[GROUP] 1.link 2.existing')
		choice = input('> (1/2, default 1): ').strip()
		members = None
		if choice == '2':
			gid, gname = Prompt.select_group(bot)
			if not gid: return None, None, None, None
			members = bot.get_members(gid)
			store_key = f'{bot.label}_{gid}'
			saved = Prompt.ask_use_saved_targets(store_key, members)
			if saved:
				return gid, gname, saved, members
			targets = Prompt.select_members_from_list(members, gname)
		else:
			gid, gname, members = Prompt.select_group_by_link(bot)
			if not gid: return None, None, None, None
			store_key = f'{bot.label}_{gid}'
			saved = Prompt.ask_use_saved_targets(store_key, members)
			if saved:
				return gid, gname, saved, members
			targets = Prompt.select_members_from_list(members, gname)
		if not targets:
			Logger.force('[ERR] no targets')
			return None, None, None, None
		TargetStore.save(store_key, targets)
		return gid, gname, targets, members

	def _setup_common(self, bot, need_mention=False, need_limit=True):
		gid, gname, targets, members = self._get_group_and_targets(bot)
		if not gid: return None
		Logger.force(f'\n[OK] {len(targets)} target(s):')
		for uid, name in targets.items():
			Logger.force(f'  - {name} ({uid})')
		texts, path = Prompt.select_file()
		if not texts: return None
		picker = TextPicker(texts, Prompt.select_mode())
		cfg = {'gid': gid, 'gname': gname, 'targets': targets, 'picker': picker, 'path': path, 'texts': texts}
		if need_mention:
			if need_limit:
				cfg['msg_limit'] = Prompt.input_int('> mention limit before rest (default 20): ', 20)
			cfg['delay_mention'] = Prompt.input_float('> delay between mentions sec (default 10): ', 10.0)
		cfg['delay_check'] = Prompt.input_float('> check interval sec (default 0.5): ', 0.5)
		return cfg

	def _header(self, mode_name, cfg, extra='', bot_label=''):
		Logger.force(f'\n{"=" * 60}')
		Logger.force(f'[MODE] {mode_name}')
		if bot_label: Logger.force(f'[ACC] {bot_label}')
		Logger.force(f'[GROUP] {cfg["gname"]}')
		Logger.force(f'[TARGETS] {", ".join(cfg["targets"].values())}')
		Logger.force(f'[FILE] {cfg["path"]} ({len(cfg["texts"])} lines)')
		if extra: Logger.force(extra)
		Logger.force(f'{"=" * 60}')

	def mode_combined(self):
		bot, engine = self._select_bot()
		cfg = self._setup_common(bot, True, True)
		if not cfg: return
		self._header('COMBINED (WITH REST)', cfg, f'[LIMIT] {cfg["msg_limit"]} -> rest 25-40min', bot.label)
		stats = {'reply': 0, 'mention': 0, 'plain': 0}
		self._tab_mgr.add_tab(f'combined|{bot.label}|{cfg["gname"][:15]}', engine.run_combined,
			(cfg['gid'], cfg['targets'], cfg['picker'], cfg['delay_check'], cfg['delay_mention'], cfg['msg_limit']),
			stats, ('reply', 'mention', 'plain'))

	def mode_combined_nonstop(self):
		bot, engine = self._select_bot()
		cfg = self._setup_common(bot, True, False)
		if not cfg: return
		self._header('COMBINED NONSTOP (NO REST)', cfg, f'[DELAY] ~{cfg["delay_mention"]}s between mentions', bot.label)
		stats = {'reply': 0, 'mention': 0, 'plain': 0}
		self._tab_mgr.add_tab(f'nonstop|{bot.label}|{cfg["gname"][:15]}', engine.run_combined_nonstop,
			(cfg['gid'], cfg['targets'], cfg['picker'], cfg['delay_check'], cfg['delay_mention']),
			stats, ('reply', 'mention', 'plain'))

	def mode_reply(self):
		bot, engine = self._select_bot()
		cfg = self._setup_common(bot)
		if not cfg: return
		self._header('REPLY ONLY', cfg, '', bot.label)
		stats = {'reply': 0, 'mention': 0, 'plain': 0}
		self._tab_mgr.add_tab(f'reply|{bot.label}|{cfg["gname"][:15]}', engine.run_reply_only,
			(cfg['gid'], cfg['targets'], cfg['picker'], cfg['delay_check']),
			stats, ('reply', 'mention', 'plain'))

	def mode_mention(self):
		bot, engine = self._select_bot()
		cfg = self._setup_common(bot, True, True)
		if not cfg: return
		self._header('MENTION (WITH REST)', cfg, f'[LIMIT] {cfg["msg_limit"]} -> rest', bot.label)
		stats = {'mention': 0}
		self._tab_mgr.add_tab(f'mention|{bot.label}|{cfg["gname"][:15]}', engine.run_mention_only,
			(cfg['gid'], cfg['targets'], cfg['picker'], cfg['delay_mention'], cfg['msg_limit']),
			stats, ('mention',))

	def mode_continuous_mention(self):
		bot, engine = self._select_bot()
		gid, gname, targets, members = self._get_group_and_targets(bot)
		if not gid: return
		Logger.force(f'\n[OK] {len(targets)} target(s)')
		texts, path = Prompt.select_file()
		if not texts: return
		picker = TextPicker(texts, Prompt.select_mode())
		delay = Prompt.input_float('> delay between mentions sec (default 10): ', 10.0)
		Logger.force(f'\n{"=" * 60}')
		Logger.force(f'[MODE] CONTINUOUS MENTION (NO REST) | [{bot.label}] | {gname}')
		Logger.force(f'{"=" * 60}')
		stats = {'mention': 0}
		self._tab_mgr.add_tab(f'cont|{bot.label}|{gname[:15]}', engine.run_continuous_mention,
			(gid, targets, picker, delay), stats, ('mention',))

	def mode_multi_account(self):
		selected_bots = self._select_multi_bots()
		if not selected_bots: return
		Logger.force(f'\n[MULTI] {len(selected_bots)} accounts: {", ".join(b.label for b in selected_bots)}')
		group_link = input('\n> group link: ').strip()
		if not group_link:
			Logger.force('[ERR] empty link')
			return
		contexts = []
		for i, bot in enumerate(selected_bots):
			Logger.force(f'\n--- [{bot.label}] fetching group ---')
			result = bot.join_and_get_group(group_link)
			if not result:
				Logger.force(f'[ERR] [{bot.label}] failed')
				return
			gid = result['id']
			gname = result['name']
			members = result['members']
			Logger.force(f'[{bot.label}] group: {gname} (id: {gid}) members: {result["totalMember"]}')
			store_key = f'multi_{bot.label}_{gid}'
			saved = Prompt.ask_use_saved_targets(store_key, members)
			if saved:
				targets = saved
			else:
				Logger.force(f'\n[{bot.label}] select targets:')
				targets = Prompt.select_members_from_list(members, f'{gname} ({bot.label})')
			if not targets:
				Logger.force(f'[ERR] [{bot.label}] no targets')
				return
			TargetStore.save(store_key, targets)
			Logger.force(f'[{bot.label}] {len(targets)} target(s)')
			contexts.append(BotContext(bot, gid, targets))
		texts, path = Prompt.select_file()
		if not texts: return
		picker = TextPicker(texts, Prompt.select_mode())
		msg_limit = Prompt.input_int('> mention limit per account (default 20): ', 20)
		delay_mention = Prompt.input_float('> delay between mentions sec (default 10): ', 10.0)
		delay_check = Prompt.input_float('> check interval sec (default 0.5): ', 0.5)
		Logger.force(f'\n{"=" * 60}')
		Logger.force(f'[MODE] MULTI-ACCOUNT COMBINED')
		for ctx in contexts:
			Logger.force(f'  [{ctx.bot.label}] gid:{ctx.gid} targets:{", ".join(ctx.targets.values())}')
		Logger.force(f'{"=" * 60}')
		stats = {'reply': 0, 'mention': 0, 'plain': 0}
		multi_engine = MultiAccountEngine(contexts)
		tab_name = f'multi|{"+".join(b.label for b in selected_bots)}'
		def multi_worker(_stats, _stop):
			multi_engine.run_multi_combined(picker, delay_check, delay_mention, msg_limit, _stats, _stop)
		self._tab_mgr.add_tab(tab_name, multi_worker, (), stats, ('reply', 'mention', 'plain'))

	def manage_accounts(self):
		while True:
			Logger.force(f'\n{"=" * 40}')
			Logger.force(f'  ACCOUNTS ({len(self._bots)}):')
			for i, b in enumerate(self._bots, 1):
				Logger.force(f'    {i}. {b.label}')
			Logger.force(f'  a.add  r.remove  o.log({("ON" if Logger.is_on() else "OFF")})  b.back')
			Logger.force(f'{"=" * 40}')
			ch = input('> ').strip().lower()
			if ch == 'a': self._add_account()
			elif ch == 'r':
				if len(self._bots) <= 1:
					Logger.force('[WARN] last account')
					continue
				try:
					idx = int(input('> number: ').strip()) - 1
					if 0 <= idx < len(self._bots):
						rm = self._bots.pop(idx)
						self._engines.pop(idx)
						Logger.force(f'[OK] removed [{rm.label}]')
				except: Logger.force('[ERR]')
			elif ch == 'o': Logger.force(f'[LOG] {"ON" if Logger.toggle() else "OFF"}')
			elif ch == 'b': break

	def run(self):
		self.init()
		while True:
			Logger.force(f'\n{"=" * 50}')
			Logger.force('          ===== MAIN MENU =====')
			Logger.force(f'{"=" * 50}')
			Logger.force('  1. combined (reply + mention, with rest)')
			Logger.force('  2. reply only')
			Logger.force('  3. mention only (with rest)')
			Logger.force('  4. create sample .txt')
			Logger.force('  5. continuous mention (no rest)')
			Logger.force('  6. multi-account combined')
			Logger.force('  7. combined nonstop (reply + mention, no rest)')
			Logger.force(f'{"=" * 50}')
			Logger.force(f'  m.tabs  a.accounts  o.log({("ON" if Logger.is_on() else "OFF")})  q.quit')
			Logger.force(f'{"=" * 50}')
			ch = input('> ').strip().lower()
			if ch == '1': self.mode_combined()
			elif ch == '2': self.mode_reply()
			elif ch == '3': self.mode_mention()
			elif ch == '4': TextLoader.create(input('> filename (default hello.txt): ').strip() or 'hello.txt')
			elif ch == '5': self.mode_continuous_mention()
			elif ch == '6': self.mode_multi_account()
			elif ch == '7': self.mode_combined_nonstop()
			elif ch == 'm': self._tab_mgr.show_menu()
			elif ch == 'a': self.manage_accounts()
			elif ch == 'o': Logger.force(f'[LOG] {"ON" if Logger.toggle() else "OFF"}')
			elif ch == 'q':
				self._tab_mgr.stop_all()
				Logger.force('[BYE]')
				sys.exit(0)


if __name__ == '__main__':
	App().run()