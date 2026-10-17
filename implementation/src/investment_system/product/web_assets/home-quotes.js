/* Home "investor story" list: a small static set, each item checked word for word against its primary source
   (Berkshire Hathaway shareholder letters on berkshirehathaway.com, read 2026-10-17). Philosophy content only: never a
   recommendation, a signal or evidence of performance. No external quote API; nothing here is fetched.
   type DIRECT = the original sentence(s) exactly as printed; STORY = a Korean summary of a passage, with the printed
   sentence it rests on in `original`. `ko` is our translation/summary and is always labelled as such. Items that could
   not be verified against a primary source are not listed. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.HomeQuotes=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const BRK='Berkshire Hathaway Inc. shareholder letter',CHECKED='2026-10-17';
 const QUOTES=Object.freeze([
  {id:'brk-2008-price-value',type:'DIRECT',
   original:'Long ago, Ben Graham taught me that “Price is what you pay; value is what you get.” Whether we’re talking about socks or stocks, I like buying quality merchandise when it is marked down.',
   headline_en:'Price is what you pay; value is what you get.',
   ko:'가격은 지불하는 것이고, 가치는 얻는 것이다.',
   ko_full:'오래전 벤 그레이엄은 내게 “가격은 지불하는 것이고, 가치는 얻는 것이다”라고 가르쳤습니다. 양말이든 주식이든, 나는 좋은 물건을 할인할 때 사는 것을 좋아합니다.',
   speaker:{ko:'워런 버핏 (벤저민 그레이엄의 말을 인용)',en:'Warren Buffett, quoting Benjamin Graham'},
   line:{ko:'벤저민 그레이엄의 가르침 · 버핏의 2008 주주서한에서 인용',en:'Benjamin Graham’s lesson, quoted in Buffett’s 2008 letter'},
   source:'2008 Chairman’s letter, '+BRK,date:'2009-02-27',url:'https://www.berkshirehathaway.com/letters/2008ltr.pdf',
   context:{ko:'2008년 금융위기 직후 주주서한의 투자 설명 부분. 주가가 하락한 시기에 가격과 기업 가치를 구분해 보라는 맥락입니다.',en:'From the investment discussion right after the 2008 crisis: separate the price paid from the value of the business.'}},
  {id:'brk-1986-fearful-greedy',type:'DIRECT',
   original:'Our goal is more modest: we simply attempt to be fearful when others are greedy and to be greedy only when others are fearful.',
   headline_en:'Be fearful when others are greedy and greedy only when others are fearful.',
   ko:'남들이 탐욕스러울 때 두려워하고, 남들이 두려워할 때만 탐욕스러워지려 할 뿐입니다.',
   ko_full:'우리의 목표는 더 소박합니다. 우리는 그저 남들이 탐욕스러울 때 두려워하고, 남들이 두려워할 때만 탐욕스러워지려 할 뿐입니다.',
   speaker:{ko:'워런 버핏',en:'Warren Buffett'},
   line:{ko:'워런 버핏 · 1986 주주서한',en:'Warren Buffett · 1986 letter'},
   source:'1986 Chairman’s letter, '+BRK,date:'1987-02-27',url:'https://www.berkshirehathaway.com/letters/1986.html',
   context:{ko:'버핏은 바로 앞 문장에서 시장이 오를지 내릴지 전혀 모른다고 밝힙니다. 시장 예측이 아니라, 공포와 탐욕이 번질 때 휩쓸리지 않겠다는 태도입니다.',en:'Just before this, Buffett says he has no idea where the market will go: an attitude toward fear and greed, not a forecast.'}},
  {id:'brk-1996-understandable-business',type:'DIRECT',
   original:'Your goal as an investor should simply be to purchase, at a rational price, a part interest in an easily-understandable business whose earnings are virtually certain to be materially higher five, ten and twenty years from now.',
   headline_en:'Buy, at a rational price, part of an easily-understandable business.',
   ko:'합리적인 가격에, 이해하기 쉬운 기업의 일부를 사는 것.',
   ko_full:'투자자로서 당신의 목표는 단순히, 5년·10년·20년 뒤 이익이 지금보다 상당히 높을 것이 거의 확실한, 이해하기 쉬운 기업의 일부 지분을 합리적인 가격에 사는 것이어야 합니다.',
   speaker:{ko:'워런 버핏',en:'Warren Buffett'},
   line:{ko:'워런 버핏 · 1996 주주서한',en:'Warren Buffett · 1996 letter'},
   source:'1996 Chairman’s letter, '+BRK,date:'1997-02-28',url:'https://www.berkshirehathaway.com/letters/1996.html',
   context:{ko:'투자자에게 필요한 공부는 “기업 가치를 평가하는 법”과 “시장 가격을 생각하는 법” 두 가지면 된다는 설명에 이어지는 문장입니다. 특정 종목 추천이 아닙니다.',en:'Follows the remark that investors need only two courses: how to value a business and how to think about market prices. Not a stock pick.'}},
  {id:'brk-1987-mr-market',type:'STORY',
   original:'Ben Graham, my friend and teacher, long ago described the mental attitude toward market fluctuations that I believe to be most conducive to investment success. He said that you should imagine market quotations as coming from a remarkably accommodating fellow named Mr. Market who is your partner in a private business. … Mr. Market is there to serve you, not to guide you.',
   headline_en:'Mr. Market is there to serve you, not to guide you.',
   ko:'미스터 마켓은 당신을 돕기 위해 있을 뿐, 당신을 이끌기 위해 있는 것이 아니다.',
   ko_full:'(일화 요약) 그레이엄은 시장 시세를 매일 찾아와 값을 부르는 동업자 ‘미스터 마켓’에 비유했습니다. 그는 기분에 따라 지나치게 높거나 낮은 값을 부르고, 무시당해도 개의치 않습니다. 버핏은 그의 제안이 유리할 때만 이용하고, 그의 기분을 판단의 기준으로 삼지 말라고 정리합니다.',
   speaker:{ko:'워런 버핏 (벤저민 그레이엄의 비유)',en:'Warren Buffett, on Benjamin Graham’s allegory'},
   line:{ko:'그레이엄의 ‘미스터 마켓’ · 버핏의 1987 주주서한',en:'Graham’s “Mr. Market” · Buffett’s 1987 letter'},
   source:'1987 Chairman’s letter, '+BRK,date:'1988-02-29',url:'https://www.berkshirehathaway.com/letters/1987.html',
   context:{ko:'시장 변동을 대하는 마음가짐에 관한 단락입니다. 가격 변동은 기회일 수 있지만 판단을 대신하지 않는다는 비유입니다.',en:'A passage on the attitude toward market fluctuations: prices can offer chances but never replace your own judgement.'}},
  {id:'brk-2013-farm',type:'STORY',
   original:'In 1986, I purchased a 400-acre farm, located 50 miles north of Omaha, from the FDIC. … With my two small investments, I thought only of what the properties would produce and cared not at all about their daily valuations.',
   headline_en:'I thought only of what the properties would produce.',
   ko:'자산이 무엇을 만들어 낼지만 생각했고, 매일의 평가액은 신경 쓰지 않았다.',
   ko_full:'(일화 요약) 1986년 버핏은 오마하 북쪽의 농장을 샀습니다. 농사는 몰랐지만 수확량과 비용으로 정상 수익을 추정했고, 매일의 시세가 아니라 농장이 만들어 낼 산출에만 집중했다고 회고합니다.',
   speaker:{ko:'워런 버핏',en:'Warren Buffett'},
   line:{ko:'워런 버핏의 농장 이야기 · 2013 주주서한',en:'Buffett’s farm story · 2013 letter'},
   source:'2013 Chairman’s letter (“Some Thoughts About Investing”), '+BRK,date:'2014-02-28',url:'https://www.berkshirehathaway.com/letters/2013ltr.pdf',
   context:{ko:'“투자에 관한 몇 가지 생각” 단락의 개인 투자 일화입니다. 수익률이나 성과의 증거로 쓰지 않습니다.',en:'A personal anecdote from “Some Thoughts About Investing”. Not used as evidence of returns or performance.'}},
  {id:'brk-2013-playing-field',type:'DIRECT',
   original:'Games are won by players who focus on the playing field – not by those whose eyes are glued to the scoreboard.',
   headline_en:'Games are won by players who focus on the playing field.',
   ko:'경기는 경기장에 집중하는 선수가 이긴다. 전광판에 눈을 고정한 선수가 아니라.',
   ko_full:'경기는 경기장에 집중하는 선수가 이깁니다. 전광판에 눈을 붙이고 있는 선수가 아니라.',
   speaker:{ko:'워런 버핏',en:'Warren Buffett'},
   line:{ko:'워런 버핏 · 2013 주주서한',en:'Warren Buffett · 2013 letter'},
   source:'2013 Chairman’s letter (“Some Thoughts About Investing”), '+BRK,date:'2014-02-28',url:'https://www.berkshirehathaway.com/letters/2013ltr.pdf',
   context:{ko:'농장과 상가 투자 일화 뒤에 이어지는 문장으로, 매일의 시세(전광판)보다 기업과 자산의 실제(경기장)를 보라는 뜻입니다.',en:'Follows the farm and retail-property anecdotes: watch the business (the field), not the daily quote (the scoreboard).'}}
 ].map(q=>Object.freeze({...q,checked_at:CHECKED,check:'PRIMARY_SOURCE_TEXT_MATCH'})));
 // Random pick that avoids an immediate repeat; `random` is injectable for tests.
 function pick(previousId,random=Math.random){const pool=QUOTES.filter(q=>q.id!==previousId);const list=pool.length?pool:QUOTES;return list[Math.min(list.length-1,Math.floor(random()*list.length))];}
 const byId=id=>QUOTES.find(q=>q.id===id)||null;
 return Object.freeze({QUOTES,pick,byId});
});
