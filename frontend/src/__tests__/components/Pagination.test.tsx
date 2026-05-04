import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Pagination from '../../components/Pagination'

describe('Pagination Component', () => {
  const defaultProps = {
    currentPage: 1,
    totalPages: 5,
    onPageChange: vi.fn(),
    totalItems: 50,
    itemsPerPage: 10
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render pagination controls', () => {
    render(<Pagination {...defaultProps} />)
    const pageButtons = screen.getAllByText('1')
    expect(pageButtons.length).toBeGreaterThan(0)
  })

  it('should show total items range', () => {
    render(<Pagination {...defaultProps} />)
    expect(screen.getByText(/Showing/)).toBeInTheDocument()
  })

  it('should call onPageChange when page clicked', async () => {
    const user = userEvent.setup()
    const onPageChange = vi.fn()
    render(<Pagination {...defaultProps} onPageChange={onPageChange} />)
    const page2Buttons = screen.getAllByText('2')
    await user.click(page2Buttons[0])
    expect(onPageChange).toHaveBeenCalledWith(2)
  })

  it('should disable prev on first page', () => {
    render(<Pagination {...defaultProps} currentPage={1} />)
    const buttons = document.querySelectorAll('button')
    expect(buttons[0]).toBeDisabled()
  })

  it('should disable next on last page', () => {
    render(<Pagination {...defaultProps} currentPage={5} />)
    const buttons = document.querySelectorAll('button')
    expect(buttons[buttons.length - 1]).toBeDisabled()
  })

  it('should render with custom items per page', () => {
    render(<Pagination {...defaultProps} itemsPerPage={25} totalItems={50} />)
    expect(screen.getByText(/Showing 1 to 25/)).toBeInTheDocument()
  })

  it('should handle single page', () => {
    render(<Pagination {...defaultProps} totalItems={5} totalPages={1} currentPage={1} />)
    expect(screen.getByText(/\d+/)).toBeInTheDocument()
  })

  it('should show ellipsis for many pages', () => {
    render(<Pagination {...defaultProps} currentPage={3} totalPages={10} />)
    expect(screen.getByText('...')).toBeInTheDocument()
  })
})