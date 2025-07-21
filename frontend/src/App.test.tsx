/**
 * App.test.tsx
 * ------------
 * Basic test file for the <App /> component using React Testing Library.
 *
 * - Renders the App and checks for the presence of the 'learn react' link.
 * - Serves as a template for adding more comprehensive tests.
 * - To expand: Add more tests for navigation, authentication, and UI rendering.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders learn react link', () => {
  render(<App />);
  const linkElement = screen.getByText(/learn react/i);
  expect(linkElement).toBeInTheDocument();
});
