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
    expect(screen.getByText('HomeIOT')).toBeInTheDocument();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Devices')).toBeInTheDocument();
    expect(screen.getByText('Modules')).toBeInTheDocument();
    expect(screen.getByText('OTA')).toBeInTheDocument();
    expect(screen.getByText('Users')).toBeInTheDocument();
    expect(screen.getByText('Dev Commands')).toBeInTheDocument();
  });

  it('renders Sign out button', () => {
    renderWithProviders(<AppLayout />);
    expect(screen.getByText('Sign out')).toBeInTheDocument();
  });
});
