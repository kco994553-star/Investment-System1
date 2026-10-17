// S08 기술적 분석: not opened here. Charts wait for their start conditions and a separate owner approval (queue §10), and
// the public files carry no prices. The device-side chart stays in the existing cockpit.
import { head, card, chip } from '../ui.js';

export function technical() {
  return head({ flow: '2', eyebrow: 'TECHNICAL', title: '기술적 분석', lede: '가격 상태·국면·실행 구간 (표시 전용, QGV 점수와 합치지 않음)' })
    + card('준비 상태', `<div class="row">${chip('준비 중', 'na')}</div>
      <ul class="list small spaced">
        <li>공개 자료에는 가격이 없어 이 화면에서 차트·지표를 그리지 않습니다.</li>
        <li>차트 기능은 착수 조건과 별도 승인 뒤에 엽니다(실행 대기열 §10).</li>
        <li>가격을 이 기기에 넣는 차트·이동평균은 기존 코크핏에 있습니다.</li>
      </ul>
      <p><a href="../#technical">기존 코크핏의 기술 화면 열기 →</a></p>`, 'data-card="technical-status"');
}
