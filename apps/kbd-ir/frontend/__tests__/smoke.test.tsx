import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import HomePage from '../pages/index';

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient();
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('HomePage', () => {
  it('renders loading state', () => {
    renderWithClient(<HomePage />);
    expect(screen.getByText('読み込み中...')).toBeInTheDocument();
  });
});
