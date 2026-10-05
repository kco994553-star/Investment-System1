import { useState, type ReactNode } from 'react';
import { chartSampleView } from './chartSampleView';
import './ChartStrategyThemeSAMPLEACTUALUnavailable.css';
const Card = ({
  title,
  children,
  dimension,
  state
}: {
  title: string;
  children: ReactNode;
  dimension: string;
  state: string;
}) => <section className="mp-chart-card" data-dimension={dimension} data-availability={state}>
    <h2>{title}</h2>{children}
  </section>;
export const ChartStrategyThemeSAMPLEACTUALUnavailable = () => {
  const [basis, setBasis] = useState<'TARGET' | 'ACTUAL'>('TARGET');
  const reference = chartSampleView.reference;
  const actual = chartSampleView.actual;
  const current = basis === 'TARGET' ? reference : actual;
  return <main className="mp-chart" data-basis={basis}>
      <header className="mp-chart-header">
        <p className="mp-chart-eyebrow">Investment-System1 · Chart review</p>
        <h1>{reference.title}</h1>
        <span className="mp-chart-badge">SAMPLE · 검증용 화면</span>
        <p role="status" aria-live="polite" data-testid="basis-status">{current.status}</p>
        <div className="mp-chart-modes" role="group" aria-label="TARGET과 ACTUAL 표시 선택">
          <button type="button" aria-pressed={basis === 'TARGET'} onClick={() => setBasis('TARGET')}>TARGET · 기존 목표비중 참고자료</button>
          <button type="button" aria-pressed={basis === 'ACTUAL'} onClick={() => setBasis('ACTUAL')}>ACTUAL · 자료 없음</button>
        </div>
        <p className="mp-chart-meta" data-testid="source-meta">{current.meta}</p>
        <p className="mp-chart-warning">현재 production TARGET source·Security·Theme·Product authority 미채택. 실제 계좌나 LIVE 결과가 아닙니다.</p>
      </header>
      {basis === 'ACTUAL' ? actual.sections.map(s => <Card key={s.dimension} title={s.title} dimension={s.dimension} state={s.state}>
          {s.paragraphs.map(p => <p className="mp-chart-warning" key={p}>{p}</p>)}
        </Card>) : reference.sections.map(s => <Card key={s.dimension} title={s.title} dimension={s.dimension} state={s.state}>
          {s.paragraphs.map(p => <p className={p.startsWith('NOT_AVAILABLE') ? 'mp-chart-warning' : ''} key={p}>{p}</p>)}
          {'svg' in s && s.svg ? <div className="mp-chart-donut">
            <div className="mp-chart-plot" dangerouslySetInnerHTML={{
          __html: s.svg
        }} />
            <ul aria-label="Strategy Theme 범례 — 전체 분모">
              {s.legend.map(item => <li key={item.label} style={{
            borderLeftColor: item.color
          }}>{item.label}</li>)}
            </ul>
          </div> : null}
          {s.typeItems.length ? <div className="mp-chart-type-grid">{s.typeItems.map(item => <article className="mp-chart-type" key={item.title}><h3>{item.title}</h3><p className="mp-chart-warning">{item.body}</p></article>)}</div> : null}
        </Card>)}
      <footer><p>SAMPLE · GICS / Strategy Theme / Investment Type / Type Overlap을 분리합니다.</p>
        <p>TARGET은 기존 참고자료입니다. ACTUAL 결측을 TARGET으로 대체하지 않습니다. 알려지지 않은 값은 0으로 표시하지 않습니다.</p>
        <p>GitHub PR #41의 기존 renderer에서 고정한 문구·SVG·단위를 사용합니다. 관측·추출 stamp는 효력 시점이 아닙니다.</p>
      </footer>
    </main>;
};