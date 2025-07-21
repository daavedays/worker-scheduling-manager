/**
 * reportWebVitals.ts
 * ------------------
 * Utility for measuring and reporting web performance metrics (Web Vitals).
 *
 * - Exports a function that, if provided a callback, will measure and report metrics like CLS, FID, FCP, LCP, TTFB.
 * - Used for performance monitoring and analytics.
 * - Optional: can be removed if not using web-vitals.
 *
 * Usage:
 *   import reportWebVitals from './reportWebVitals';
 *   reportWebVitals(console.log); // or send to analytics endpoint
 */
import { ReportHandler } from 'web-vitals';

const reportWebVitals = (onPerfEntry?: ReportHandler) => {
  if (onPerfEntry && onPerfEntry instanceof Function) {
    import('web-vitals').then(({ getCLS, getFID, getFCP, getLCP, getTTFB }) => {
      getCLS(onPerfEntry);
      getFID(onPerfEntry);
      getFCP(onPerfEntry);
      getLCP(onPerfEntry);
      getTTFB(onPerfEntry);
    });
  }
};

export default reportWebVitals;
