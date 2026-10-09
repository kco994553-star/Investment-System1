import { Theme } from './settings/types';
import { ChartStrategyThemeSAMPLEACTUALUnavailable } from './components/generated/ChartStrategyThemeSAMPLEACTUALUnavailable';

let theme: Theme = 'light';

function App() {
  function setTheme(theme: Theme) {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }

  setTheme(theme);

  return (
    <>
      <ChartStrategyThemeSAMPLEACTUALUnavailable />
    </>
  ); // %EXPORT_STATEMENT%
}

export default App;
