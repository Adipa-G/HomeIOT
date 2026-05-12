import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '../test-utils';
import { AppLayout } from '../../layouts/AppLayout';

describe('AppLayout', () => {
  beforeEach(() => {
    localStorage.setItem('auth_token', 'test-token');
  });

  it('renders sidebar navigation links', () => {
    renderWithProviders(<AppLayout />);
    expect(screen.getAllByText('HomeIOT').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Dashboard').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Devices').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Modules').length).toBeGreaterThan(0);
    expect(screen.getAllByText('OTA').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Users').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Dev Commands').length).toBeGreaterThan(0);
  });

  it('renders Sign out button', () => {
    renderWithProviders(<AppLayout />);
    expect(screen.getAllByText('Sign out').length).toBeGreaterThan(0);
  });
});
