class Jogo():
    """Classe que implementa um jogo da velha."""

    SIMBOLOS = ['X','O']

    @staticmethod
    def empty_board():
        """Retorna um tabuleiro vazio."""
        return [['','',''],
                ['','',''],
                ['','','']]

    def __init__(self, tab=None):
        if tab is None:
            self.tabuleiro = Jogo.empty_board()
        else:
            self.tabuleiro = tab

    def terminou(self):
        """Verifica se o jogo terminou. Retorna símbolo vencedor ou None"""
        # Verifica linhas
        for i in range(3):
            for s in Jogo.SIMBOLOS:
                if all(self.tabuleiro[i][j] == s for j in range(3)):
                    return s

        # Verifica colunas
        for i in range(3):
            for s in Jogo.SIMBOLOS:
                if all(self.tabuleiro[j][i] == s for j in range(3)):
                    return s

        # Verifica Diagonais
        for s in Jogo.SIMBOLOS:
            if all(self.tabuleiro[i][i] == s for i in range(3)) \
                    or all(self.tabuleiro[-i][-i] == s for i in range(3)):
                return s

        return None

    def faz_jogada(self, pos_x, pos_y, simb):
        """Coloca simb na posição (pos_x,pos_y)."""
        assert pos_x >= 0 and pos_x < 3, f"pos_x com valor invalido: {pos_x}"
        assert pos_y >= 0 and pos_y < 3, f"pos_y com valor invalido: {pos_y}"
        assert simb in Jogo.SIMBOLOS, f"simb deve ser 'X' ou 'O'"

        assert self.pode_jogar(pos_x, pos_y), \
            f"Posição ({pos_x},{pos_y}) já preenchida."

        self.tabuleiro[pos_y][pos_x] = simb
    
    def pode_jogar(self, pos_x, pos_y):
        """Verifica se a posição está livre"""
        assert pos_x >= 0 and pos_x < 3, f"pos_x com valor invalido: {pos_x}"
        assert pos_y >= 0 and pos_y < 3, f"pos_y com valor invalido: {pos_y}"

        return self.tabuleiro[pos_y][pos_x] == ''