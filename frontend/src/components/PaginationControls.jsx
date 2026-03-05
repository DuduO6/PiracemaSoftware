import React from "react";

const PaginationControls = ({
  totalItems,
  itemsPerPage = 10,
  currentPage,
  onPageChange,
}) => {
  const totalPages = Math.max(1, Math.ceil(totalItems / itemsPerPage));
  const inicio = totalItems === 0 ? 0 : (currentPage - 1) * itemsPerPage + 1;
  const fim = Math.min(currentPage * itemsPerPage, totalItems);

  if (totalItems <= itemsPerPage) return null;

  return (
    <div className="pagination-container">
      <span className="pagination-info">
        Mostrando {inicio}-{fim} de {totalItems}
      </span>
      <div className="pagination-controls">
        <button
          className="pagination-btn"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
        >
          Anterior
        </button>
        <span className="pagination-page">
          Página {currentPage} de {totalPages}
        </span>
        <button
          className="pagination-btn"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages}
        >
          Próxima
        </button>
      </div>
    </div>
  );
};

export default PaginationControls;
