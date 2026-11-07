import unittest
from frozen_french_holding_periods import holding_windows

def curve(n,r):return [{'date':f'{2000+i//12:04}-{i%12+1:02}','value':100*(1+r)**i} for i in range(n+1)]
class HoldingTests(unittest.TestCase):
 def test_complete_overlap(self):
  x=holding_windows(curve(24,.01),curve(24,0),12)
  self.assertEqual(x['window_count'],13)
  self.assertAlmostEqual(x['summary']['cumulative_return']['mean'],1.01**12-1)
  self.assertEqual(x['summary']['market_win_fraction'],1)
  self.assertEqual(x['windows'][0]['start_nav_month'],'2000-01')
  self.assertEqual(x['windows'][-1]['end_month'],'2002-01')
 def test_short_is_null(self):
  x=holding_windows(curve(11,.01),curve(11,0),12)
  self.assertIsNone(x['summary']);self.assertEqual(x['window_count'],0)
 def test_date_gap_and_alignment(self):
  a=curve(24,.01);b=curve(24,.01);del b[4]
  with self.assertRaisesRegex(ValueError,'NONCONTIGUOUS'):holding_windows(a,b,12)
  with self.assertRaisesRegex(ValueError,'MISMATCH'):holding_windows(a,b[:3],12)
 def test_multiyear_and_drawdown(self):
  x=holding_windows(curve(36,-.01),curve(36,0),36);s=x['summary']
  self.assertEqual(x['window_count'],1)
  self.assertAlmostEqual(s['annualized_return']['mean'],.99**12-1)
  self.assertAlmostEqual(s['max_drawdown']['worst'],.99**36-1)
  self.assertEqual(s['loss_fraction'],1)
 def test_tie_not_win(self):
  a=curve(120,.01);s=holding_windows(a,a,120)['summary']
  self.assertEqual(s['market_win_fraction'],0);self.assertEqual(s['market_tie_fraction'],1)
if __name__=='__main__':unittest.main()
