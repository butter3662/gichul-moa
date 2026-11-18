import json,re,collections
t=json.load(open('data/texts.json'))
def toks(s): return set(re.findall(r'[가-힣A-Za-z]{2,}',s or ''))
STOP=toks('그림 대한 설명 옳은 것만을 보기 있는 대로 고른 것은 이에 나타낸 것이다 각각 중 하나이다 이다 이므로 따라서 출제의도 이해한다 오답풀이 정답 값은 순서 없이 다음은 자료 같다 크다 작다 보다 일정하다')
g=collections.defaultdict(list)
for k,v in t.items():
  if not v['e'].strip(): continue
  q=toks(v['q'])-STOP; e=toks(v['e'])-STOP
  if len(q)<5: continue
  g[k.rsplit('|',2)[0]].append(len(q&e)/len(q))
bad=[(sum(x)/len(x),k,len(x)) for k,x in g.items()]
bad.sort()
for r in bad[:40]: print('%.2f'%r[0],r[1],r[2])
